"""Loopback session control and passive bounded replay/stream reads."""
import asyncio
from contextlib import asynccontextmanager
from functools import lru_cache
import hashlib
import hmac
from pathlib import Path
import secrets
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .contracts import LiveConfig, LiveHealth, SourceCapability
from .flight import SyntheticFlightPreview, synthetic_preview
from .accounting import BusyError
from .api_contracts import (ApiSnapshot, ControlBootstrap, InspectRequest, OwnerRequest, PreviewReply, PreviewRequest,
                            ServiceStatus, SourceList, StartRequest)
from .service import Conflict, Forbidden, LiveService, NotFound, Unavailable
from .recording import RecordingError, ReplayList, ReplayPayload
from .flight import FlightState

DIST = Path(__file__).resolve().parents[2] / "web/dist"


def create_live_app(*, dist: Path = DIST, service=None):
    service = service or LiveService()
    signing_key = secrets.token_bytes(32)

    @asynccontextmanager
    async def lifespan(app):
        await service.open()
        try:
            yield
        finally:
            await service.close()

    app = FastAPI(title="Flyjam local sessions", version="OBS05", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.service = service
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def private_response(request, call_next):
        protected = request.url.path.startswith(("/api/live/sessions", "/api/live/preview", "/api/live/sources/inspect"))
        if request.method == "POST" and protected:
            origin = f"{request.url.scheme}://{request.headers.get('host')}"
            if request.headers.get("origin") != origin:
                return JSONResponse(status_code=403, content={"detail": "Same-origin control required."})
            token = request.cookies.get("live_csrf", "")
            nonce, _, signature = token.partition(".")
            expected = hmac.new(signing_key, nonce.encode(), hashlib.sha256).hexdigest()
            if (len(nonce) != 32 or not hmac.compare_digest(signature, expected)
                    or not hmac.compare_digest(token, request.headers.get("x-live-csrf", ""))):
                return JSONResponse(status_code=403, content={"detail": "Local control token required."})
            if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
                return JSONResponse(status_code=415, content={"detail": "JSON required."})
            body = bytearray()
            try:
                async with asyncio.timeout(2):
                    async for chunk in request.stream():
                        if len(body) + len(chunk) > 8192:
                            return JSONResponse(status_code=413, content={"detail": "Control body exceeds 8192 bytes."})
                        body.extend(chunk)
            except TimeoutError:
                return JSONResponse(status_code=408, content={"detail": "Control body deadline exceeded."})
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Existing AJV browser validators compile bundled, trusted schemas.
        # No client-supplied schema/code or remote scripts are accepted.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-eval'; "
            "frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
        )
        if request.url.path == "/live/obs-test":
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                "frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
            )
        return response

    for error, code in ((BusyError, 409), (Conflict, 409), (Forbidden, 403),
                        (NotFound, 404), (Unavailable, 503), (RecordingError, 422)):
        async def handle(request, exc, status_code=code):
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})
        app.add_exception_handler(error, handle)

    @app.exception_handler(OSError)
    async def storage_unavailable(request, exc):
        return JSONResponse(status_code=503, content={"detail": "Local source or storage unavailable."})

    @app.get("/api/live/control", response_model=ControlBootstrap)
    def control(request: Request, response: Response):
        token = request.cookies.get("live_csrf", "")
        nonce, _, signature = token.partition(".")
        expected = hmac.new(signing_key, nonce.encode(), hashlib.sha256).hexdigest()
        if len(nonce) != 32 or not hmac.compare_digest(signature, expected):
            nonce = secrets.token_hex(16)
            token = nonce + "." + hmac.new(signing_key, nonce.encode(), hashlib.sha256).hexdigest()
        response.set_cookie("live_csrf", token, httponly=True, samesite="strict", path="/api/live")
        return ControlBootstrap(csrf_token=token)

    @app.get("/api/live/sources", response_model=SourceList)
    def sources():
        return service.sources()

    @app.post("/api/live/sources/inspect", response_model=SourceCapability)
    def inspect_source(request: InspectRequest):
        return service.inspect(request.source_id)

    @app.post("/api/live/sessions", response_model=ApiSnapshot)
    def start(request: StartRequest):
        return service.start(request)

    @app.post("/api/live/preview", response_model=ApiSnapshot)
    def start_preview(request: PreviewRequest):
        return service.start(request, preview=True)

    @app.get("/api/live/status", response_model=ServiceStatus)
    def status():
        return ServiceStatus(current=service.snapshot(service.current_id) if service.current_id else None)

    @app.get("/api/live/sessions/{session_id}", response_model=ApiSnapshot)
    def snapshot(session_id: str):
        return service.snapshot(session_id)

    @app.get("/api/live/sessions/{session_id}/preview", response_model=PreviewReply)
    def current_preview(session_id: str):
        return service.preview(session_id)

    @app.post("/api/live/sessions/{session_id}/renew", response_model=ApiSnapshot)
    def renew(session_id: str, request: OwnerRequest):
        return service.control(session_id, request)

    @app.post("/api/live/sessions/{session_id}/stop", response_model=ApiSnapshot)
    def stop(session_id: str, request: OwnerRequest):
        return service.control(session_id, request, stop=True)

    @app.get("/api/live/sessions/{session_id}/events")
    async def events(session_id: str, request: Request, generation: Annotated[int, Query(ge=1)]):
        try:
            client_id, queue = await service.subscribe(session_id, generation)
        except BusyError as exc:
            raise HTTPException(429, str(exc)) from None

        async def stream():
            try:
                while not await request.is_disconnected():
                    packet = await queue.get()
                    # A capacity-one queue and bounded transport write mean a slow
                    # client never blocks model/capture threads or builds history.
                    yield (f"id: {session_id}:{generation}:{packet.event_sequence}\n"
                           f"event: snapshot\ndata: {packet.model_dump_json()}\n\n")
                    if packet.status.state in {"stopped", "failed", "source_lost", "limit_reached"}:
                        return
            finally:
                service.unsubscribe(client_id)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    def store():
        # Constructor/read paths never create storage or open source/model handles.
        from .recording import RecordingStore
        return service.recording_store or RecordingStore(service.root / "artifacts/live/recordings")

    @app.get("/api/live/replays", response_model=ReplayList)
    def replays():
        try:
            return ReplayList(recordings=store().list())
        except (ValueError, OSError):
            raise HTTPException(503, "Recording storage is unavailable or exceeds its listing bound.") from None

    def read_replay(recording_id):
        try:
            return store().read(recording_id)
        except (ValueError, OSError):
            raise HTTPException(422, "Recording is missing, incomplete, unsupported or corrupt.") from None

    @app.get("/api/live/replays/{recording_id}", response_model=ReplayPayload)
    def recorded(recording_id: str):
        replay = read_replay(recording_id)
        return replay.payload()

    @app.get("/api/live/replays/{recording_id}/download", response_model=ReplayPayload)
    def download(recording_id: str, response: Response):
        payload = read_replay(recording_id).payload()
        # read_replay strictly validates the ID before using it in a header.
        response.headers["Content-Disposition"] = f'attachment; filename="flyjam-{recording_id}.json"'
        return payload

    @app.get("/api/live/replays/{recording_id}/seek", response_model=FlightState)
    def seek(recording_id: str, tick: Annotated[int, Query(ge=0, le=6000)]):
        try:
            return read_replay(recording_id).seek(tick)
        except ValueError:
            raise HTTPException(422, "Seek tick is outside this recording.") from None

    @app.get("/health/live", response_model=LiveHealth)
    async def health():
        return LiveHealth()

    @app.get("/api/live/config", response_model=LiveConfig)
    async def config():
        return await asyncio.to_thread(service.config)

    # Safe precomputed synthetic content only. No session, recording or inference.
    preview = lru_cache(maxsize=1)(synthetic_preview)

    @app.get("/api/live/flight-preview", response_model=SyntheticFlightPreview)
    def flight_preview():
        return preview()

    @app.get("/")
    async def home():
        return RedirectResponse("/live")

    @app.get("/live")
    async def screen():
        if not (dist / "index.html").is_file():
            raise HTTPException(503, "Build the local UI: npm --prefix web run build")
        return FileResponse(dist / "index.html")

    @app.get("/live/obs-test")
    async def obs_test():
        # Original harmless content for an operator-selected OBS Browser Source.
        return FileResponse(Path(__file__).parent / "assets/obs-test.html")

    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    return app

"""Loopback session control and passive bounded replay/stream reads."""
import asyncio
from contextlib import asynccontextmanager
from functools import lru_cache
import hashlib
import hmac
from pathlib import Path
import secrets
import threading
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .contracts import LiveConfig, LiveHealth, SourceCapability
from .flight import SyntheticFlightPreview, synthetic_preview
from .accounting import BusyError
from .api_contracts import (ApiError, ApiSnapshot, ControlBootstrap, DisplayReply, ERROR_MESSAGES,
                            InspectRequest, OwnerRequest, PreviewReply, PreviewRequest,
                            ServiceCapabilities, ServiceStatus, SourceList, StartRequest)
from .service import (Conflict, Forbidden, InferenceUnavailable, LiveService, NotFound,
                      RecordingForbidden, Unavailable)
from .recording import RecordingError, ReplayList, ReplayPayload
from .flight import FlightState

DIST = Path(__file__).resolve().parents[2] / "web/dist"


def error_response(status_code, code):
    return JSONResponse(status_code=status_code,
        content=ApiError(code=code, message=ERROR_MESSAGES[code]).model_dump(),
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


class DisplayResponse(Response):
    """Retain client admission through all ASGI sends, even pre-body disconnects."""
    def __init__(self, response, admission):
        self.response = response
        self.admission = admission

    async def __call__(self, scope, receive, send):
        try:
            await self.response(scope, receive, send)
        finally:
            self.admission.release()


def create_live_app(*, dist: Path = DIST, service=None):
    service = service or LiveService()
    signing_key = secrets.token_bytes(32)
    display_clients = threading.BoundedSemaphore(service.max_clients)

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
                return error_response(403, "origin_required")
            token = request.cookies.get("live_csrf", "")
            nonce, _, signature = token.partition(".")
            expected = hmac.new(signing_key, nonce.encode(), hashlib.sha256).hexdigest()
            if (len(nonce) != 32 or not hmac.compare_digest(signature, expected)
                    or not hmac.compare_digest(token, request.headers.get("x-live-csrf", ""))):
                return error_response(403, "csrf_required")
            if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
                return error_response(415, "json_required")
            body = bytearray()
            try:
                async with asyncio.timeout(2):
                    async for chunk in request.stream():
                        if len(body) + len(chunk) > 8192:
                            return error_response(413, "request_too_large")
                        body.extend(chunk)
            except TimeoutError:
                return error_response(408, "request_timeout")
            request._body = bytes(body)
        is_display = (request.method == "POST" and request.url.path.startswith("/api/live/sessions/")
                      and request.url.path.endswith("/display"))
        if is_display and not display_clients.acquire(blocking=False):
            return error_response(429, "client_limit")
        try:
            response = await call_next(request)
        except BaseException:
            if is_display:
                display_clients.release()
            raise
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Existing AJV browser validators compile bundled, trusted schemas.
        # No client-supplied schema/code or remote scripts are accepted.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-eval'; "
            "img-src 'self' blob:; "
            "frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
        )
        if request.url.path == "/live/obs-test":
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                "frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
            )
        # The whole response lifecycle owns admission, including header-send failure.
        return DisplayResponse(response, display_clients) if is_display else response

    for error, status, code in ((BusyError, 409, "control_busy"),
            (Conflict, 409, "control_conflict"), (Forbidden, 403, "owner_required"),
            (RecordingForbidden, 403, "recording_forbidden"),
            (NotFound, 404, "session_not_found"), (Unavailable, 503, "source_unavailable"),
            (InferenceUnavailable, 503, "inference_unavailable"),
            (RecordingError, 422, "replay_unavailable"),
            (OSError, 503, "service_unavailable"),
            (RequestValidationError, 422, "invalid_request"), (Exception, 500, "internal_error")):
        async def handle(request, exc, status_code=status, error_code=code):
            return error_response(status_code, error_code)
        app.add_exception_handler(error, handle)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        # Only the server's fixed codes are accepted, never arbitrary detail text.
        code = exc.detail if isinstance(exc.detail, str) and exc.detail in ERROR_MESSAGES else {
            404: "not_found", 422: "invalid_request", 429: "client_limit",
            503: "service_unavailable"}.get(exc.status_code, "internal_error")
        return error_response(exc.status_code, code)

    @app.get("/api/live/capabilities", response_model=ServiceCapabilities)
    def capabilities():
        return service.capabilities

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

    @app.post("/api/live/sessions/{session_id}/display", response_model=DisplayReply)
    def display_frame(session_id: str, request: OwnerRequest):
        try:
            return service.display(session_id, request)
        except BusyError:
            raise HTTPException(429, "client_limit") from None

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
        except BusyError:
            raise HTTPException(429, "client_limit") from None

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
            raise HTTPException(503, "service_unavailable") from None

    def read_replay(recording_id):
        try:
            return store().read(recording_id)
        except (ValueError, OSError):
            raise HTTPException(422, "replay_unavailable") from None

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
            raise HTTPException(422, "seek_out_of_range") from None

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
            raise HTTPException(503, "ui_unavailable")
        return FileResponse(dist / "index.html")

    @app.get("/live/obs-test")
    async def obs_test():
        # Original harmless content for an operator-selected OBS Browser Source.
        return FileResponse(Path(__file__).parent / "assets/obs-test.html")

    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    if (dist / "sg01").is_dir():
        app.mount("/sg01", StaticFiles(directory=dist / "sg01"), name="sg01")
    return app

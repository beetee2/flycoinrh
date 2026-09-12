"""Loopback-only P00 API; one bounded child job, no queue or database."""
import asyncio
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .budget import CallBudget
from .contracts import CALL_CAP, CALLS_PER_COMPARISON, LabRequest, LabResult, SEEDS

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "artifacts/milestones/P00"
MAX_BODY = 8192
MAX_RESULT = 2_000_000
TIMEOUT_SECONDS = 90


class Busy(RuntimeError):
    pass


class Unavailable(RuntimeError):
    pass


class LabService:
    def __init__(self):
        self.root = ARTIFACTS
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "results").mkdir(exist_ok=True)
        self.budget = CallBudget(self.root / "attempts.jsonl")

    @contextmanager
    def slot(self):
        with (self.root / "model.lock").open("a") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Busy("One model job is already running. Wait for it to finish.") from None
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def prerequisites(self):
        required = ("build/flytrap-v1/graph.npz", "build/flytrap-v1/manifest.json",
                    "data/body-annotations.feather", "config/flytrap-model-v1.json",
                    "config/flytrap-visual-v1.json", "artifacts/milestones/05/trials/baseline.json")
        if any(not (REPO / p).is_file() for p in required):
            raise Unavailable("Real model data or the explicit baseline is unavailable.")
        if self.budget.attempted + CALLS_PER_COMPARISON > CALL_CAP:
            raise Unavailable("P00 call budget cannot admit another 9-call comparison.")

    def status(self):
        try:
            self.prerequisites()
            with self.slot():
                pass
            state, message = "ready", "Ready for an explicit local comparison."
        except Busy as exc:
            state, message = "busy", str(exc)
        except (Unavailable, ValueError, OSError) as exc:
            state, message = "unavailable", str(exc)
        try:
            attempted = self.budget.attempted
        except (ValueError, OSError):
            attempted = CALL_CAP
        return dict(state=state, message=message, attempted_calls=attempted,
                    call_cap=CALL_CAP, seeds=list(SEEDS), calls_per_comparison=CALLS_PER_COMPARISON)

    def compare(self, request):
        with self.slot():
            self.prerequisites()
            result_id = uuid.uuid4().hex
            envelope = dict(request=request.model_dump(), result_id=result_id)
            (self.root / "results" / f"{result_id}.request.json").write_text(json.dumps(envelope))
            env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
            with (self.root / "results" / f"{result_id}.log").open("w") as log:
                try:
                    child = subprocess.run([sys.executable, "-m", "flytrap.lab.runner"],
                                           input=json.dumps(envelope).encode(), cwd=REPO, env=env,
                                           stdout=log, stderr=log, timeout=TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    raise Unavailable("Model job exceeded the 90-second limit; child stopped. Attempted calls remain counted.") from None
            if child.returncode:
                raise Unavailable(f"Model job failed (exit {child.returncode}); local evidence ID {result_id}. Attempted calls remain counted.")
            result_path = self.root / "results" / f"{result_id}.json"
            if result_path.stat().st_size > MAX_RESULT:
                raise Unavailable("Model result exceeded the byte limit.")
            return LabResult.model_validate_json(result_path.read_bytes())


def create_lab_app(service=None):
    service = service or LabService()
    app = FastAPI(title="FLYTRAP LAB — local non-production P00", version="P00")
    app.state.service = service
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin")
            if origin and origin != f"{request.url.scheme}://{request.headers.get('host')}":
                return JSONResponse(status_code=403, content={"detail": "Same-origin local requests required."})
            if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
                return JSONResponse(status_code=415, content={"detail": "JSON required."})
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_BODY:
                    return JSONResponse(status_code=413, content={"detail": "Payload exceeds 8192 bytes."})
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health/live")
    async def live():
        return {"status": "ok", "prototype": "P00", "production": False}

    @app.get("/api/lab/status")
    async def status():
        return await asyncio.to_thread(service.status)

    @app.post("/api/lab/compare", response_model=LabResult)
    async def compare(request: LabRequest):
        try:
            return await asyncio.to_thread(service.compare, request)
        except Busy as exc:
            raise HTTPException(409, str(exc)) from None
        except (Unavailable, ValueError, OSError) as exc:
            raise HTTPException(503, str(exc)) from None

    dist = REPO / "web/dist"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/")
    async def home():
        return RedirectResponse("/lab")

    @app.get("/lab")
    async def screen():
        if not (dist / "index.html").is_file():
            raise HTTPException(503, "Build the local UI first: npm --prefix web run build")
        return FileResponse(dist / "index.html")

    return app

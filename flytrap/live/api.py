"""OBS00 idle local service. No device or neural worker imports."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .contracts import LiveConfig, LiveHealth

DIST = Path(__file__).resolve().parents[2] / "web/dist"


def create_live_app(*, dist: Path = DIST):
    app = FastAPI(title="Flyjam local live foundation", version="OBS00",
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def private_response(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Existing AJV browser validators compile bundled, trusted schemas.
        # No client-supplied schema/code or remote scripts are accepted.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-eval'; "
            "frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
        )
        return response

    @app.get("/health/live", response_model=LiveHealth)
    async def health():
        return LiveHealth()

    @app.get("/api/live/config", response_model=LiveConfig)
    async def config():
        return LiveConfig()

    @app.get("/")
    async def home():
        return RedirectResponse("/live")

    @app.get("/live")
    async def screen():
        if not (dist / "index.html").is_file():
            raise HTTPException(503, "Build the local UI: npm --prefix web run build")
        return FileResponse(dist / "index.html")

    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    return app

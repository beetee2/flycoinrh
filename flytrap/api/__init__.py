"""Health/config only. Public challenge/run endpoints are deferred to milestone 08."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from flytrap.config import Settings
from flytrap.contracts import Capabilities, ErrorResponse
from flytrap.persistence import connect_database
from flytrap.worker import create_worker


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        settings.artifact_root.mkdir(parents=True, exist_ok=True)
        with connect_database(settings.database_path) as connection:
            connection.execute("SELECT 1").fetchone()
        app.state.started = True
        try:
            if settings.profile == "fixture":
                app.state.worker = create_worker(settings)
                app.state.worker.start()
            yield
        finally:
            if app.state.worker is not None:
                app.state.worker.close()
            app.state.started = False

    app = FastAPI(title="FLYTRAP foundation", version="0.1.0", lifespan=lifespan)
    app.state.started = False
    app.state.worker = None
    app.state.settings = settings

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready", responses={503: {"model": ErrorResponse}})
    def ready():
        worker = app.state.worker
        if app.state.started and worker is not None and worker.alive:
            return {"status": "ready", "fixture": True, "admission": "closed"}
        error = ErrorResponse(
            schema_version="1", code="unavailable", retryable=False,
            message="Real-model integration is not available." if settings.profile == "real"
            else "Fixture worker is not ready.",
        )
        return JSONResponse(status_code=503, content=error.model_dump())

    @app.get("/api/config", response_model=Capabilities)
    def capabilities():
        return Capabilities(
            schema_version="1", fixture=settings.profile == "fixture", real_model_available=False,
            admission="closed" if settings.profile == "fixture" else "unavailable",
            learning_claim_status="NOT_RUN", approved_checkpoint_ids=[], approved_comparison_ids=[],
        )

    return app

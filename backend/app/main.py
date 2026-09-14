"""ChennaiFlood-Twin API application factory.

Run locally:  uvicorn app.main:app --reload   (from the backend/ directory)
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import flood, gis, health, scenarios, simulations
from app.core.config import APP_VERSION, Settings, get_settings
from app.core.container import Container
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, log_event

logger = logging.getLogger("app")

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        c = container or Container.build(settings)
        app.state.container = c
        recovered = c.simulations.recover_interrupted()
        log_event(logger, "app.started", env=settings.app_env, model_version=settings.model_version, recovered_runs=len(recovered) or None)
        try:
            yield
        finally:
            c.executor.shutdown()
            c.engine.dispose()
            log_event(logger, "app.stopped")

    app = FastAPI(
        title="ChennaiFlood-Twin API",
        version=APP_VERSION,
        description="Backend for the Ward 176 urban flood Digital Twin: scenarios, controlled EPA SWMM simulations, model-derived results and web-ready GIS layers.",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        incoming = request.headers.get("x-request-id", "")
        request.state.request_id = incoming if 0 < len(incoming) <= 64 and incoming.replace("-", "").isalnum() else f"req-{uuid.uuid4().hex[:12]}"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID", "If-None-Match"],
        expose_headers=["X-Request-ID", "ETag", "Location"],
    )
    register_exception_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    for module in (health, scenarios, simulations, flood, gis):
        api.include_router(module.router)
    app.include_router(api)
    return app


app = create_app()

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.config import Settings
from app.errors import register_exception_handlers
from app.repositories.database import DatabaseRepository, create_database_engine
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.historial import router as historial_router
from app.routes.mascotas import router as mascotas_router
from app.routes.solicitudes import router as solicitudes_router
from app.services.auth import AuthService
from app.services.health import HealthService
from app.services.historial import HistorialService
from app.services.mascotas import MascotaService
from app.services.solicitudes import SolicitudService


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    logging.basicConfig(
        level=app_settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    engine = create_database_engine(app_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="B-Personal API",
        description=(
            "Backend API for animal adoption and health management. "
            "Errors use the shared response envelope: "
            "`success=false`, `status=error`, `message` and `error.message`. "
            "Request validation failures return HTTP 400."
        ),
        lifespan=lifespan,
    )
    app.state.health_service = HealthService(DatabaseRepository(engine))
    app.state.mascota_service = MascotaService(engine)
    app.state.solicitud_service = SolicitudService(engine)
    app.state.historial_service = HistorialService(engine)
    app.state.auth_service = AuthService(engine, app_settings)
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(mascotas_router)
    app.include_router(solicitudes_router)
    app.include_router(historial_router)

    register_exception_handlers(app)
    app.openapi = lambda: _openapi_schema(app)

    return app


def _openapi_schema(app: FastAPI) -> dict[str, object]:
    if app.openapi_schema is not None:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict):
                operation.get("responses", {}).pop("422", None)
    app.openapi_schema = schema
    return schema


app = create_app()

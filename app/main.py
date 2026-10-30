import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import Settings
from app.repositories.database import DatabaseRepository, create_database_engine
from app.repositories.mascotas import DatabaseUnavailableError
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.mascotas import router as mascotas_router
from app.services.auth import (
    AuthService,
    AuthenticationConfigurationError,
)
from app.services.health import HealthService
from app.services.mascotas import MascotaNotFoundError, MascotaService


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    logging.basicConfig(
        level=app_settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    engine = create_database_engine(app_settings)
    logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="B-Personal API",
        description="Backend API for animal adoption and health management.",
        lifespan=lifespan,
    )
    app.state.health_service = HealthService(DatabaseRepository(engine))
    app.state.mascota_service = MascotaService(engine)
    app.state.auth_service = AuthService(engine, app_settings)
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(mascotas_router)

    @app.exception_handler(MascotaNotFoundError)
    async def mascota_not_found_handler(
        _: Request, error: MascotaNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error_response(str(error)),
        )

    @app.exception_handler(DatabaseUnavailableError)
    async def database_unavailable_handler(
        _: Request, error: DatabaseUnavailableError
    ) -> JSONResponse:
        logger.warning("Mascotas database operation unavailable (%s)", type(error).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_error_response("Database unavailable"),
        )

    @app.exception_handler(AuthenticationConfigurationError)
    async def authentication_configuration_error_handler(
        _: Request, error: AuthenticationConfigurationError
    ) -> JSONResponse:
        logger.error("Authentication is not configured (%s)", type(error).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_error_response("Authentication service is not configured"),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_: Request, error: IntegrityError) -> JSONResponse:
        logger.info("Mascotas database constraint rejected a request (%s)", type(error).__name__)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_response("A referenced resource does not exist or violates a constraint"),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_: Request, error: SQLAlchemyError) -> JSONResponse:
        logger.error("Mascotas database operation failed (%s)", type(error).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_error_response("Database operation failed"),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        _: Request, error: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
            }
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_response("Invalid request data", errors=details),
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, error: HTTPException) -> JSONResponse:
        message = error.detail if isinstance(error.detail, str) else "Request failed"
        return JSONResponse(
            status_code=error.status_code,
            headers=error.headers,
            content=_error_response(message),
        )

    return app


def _error_response(message: str, **extra: object) -> dict[str, object]:
    return {
        "success": False,
        "status": "error",
        "message": message,
        "error": {"message": message},
        **extra,
    }


app = create_app()

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.repositories.mascotas import DatabaseUnavailableError
from app.services.auth import AuthenticationConfigurationError
from app.services.historial import HistorialNotFoundError
from app.services.mascotas import MascotaNotFoundError
from app.services.policies import BusinessRuleViolationError, ResourceAccessDeniedError
from app.services.solicitudes import SolicitudNotFoundError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    for exception_type in (
        MascotaNotFoundError,
        SolicitudNotFoundError,
        HistorialNotFoundError,
    ):
        app.add_exception_handler(exception_type, resource_not_found_handler)

    app.add_exception_handler(ResourceAccessDeniedError, forbidden_handler)
    app.add_exception_handler(BusinessRuleViolationError, business_rule_handler)
    app.add_exception_handler(DatabaseUnavailableError, database_unavailable_handler)
    app.add_exception_handler(
        AuthenticationConfigurationError, authentication_unavailable_handler
    )
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)


async def resource_not_found_handler(
    _: Request, error: Exception
) -> JSONResponse:
    return error_response(status.HTTP_404_NOT_FOUND, str(error))


async def forbidden_handler(_: Request, error: Exception) -> JSONResponse:
    return error_response(status.HTTP_403_FORBIDDEN, str(error))


async def business_rule_handler(_: Request, error: Exception) -> JSONResponse:
    return error_response(status.HTTP_400_BAD_REQUEST, str(error))


async def database_unavailable_handler(
    _: Request, error: DatabaseUnavailableError
) -> JSONResponse:
    logger.warning("Database unavailable error_type=%s", type(error).__name__)
    return error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Database unavailable"
    )


async def authentication_unavailable_handler(
    _: Request, error: AuthenticationConfigurationError
) -> JSONResponse:
    logger.error("Authentication unavailable error_type=%s", type(error).__name__)
    return error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Authentication service is not configured",
    )


async def integrity_error_handler(
    _: Request, error: IntegrityError
) -> JSONResponse:
    logger.info("Database constraint rejected request error_type=%s", type(error).__name__)
    return error_response(
        status.HTTP_400_BAD_REQUEST,
        "A referenced resource does not exist or violates a constraint",
    )


async def database_error_handler(
    _: Request, error: SQLAlchemyError
) -> JSONResponse:
    logger.error("Database operation failed error_type=%s", type(error).__name__)
    return error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Database operation failed"
    )


async def validation_error_handler(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in item["loc"]),
            "message": item["msg"],
        }
        for item in error.errors()
    ]
    return error_response(
        status.HTTP_400_BAD_REQUEST,
        "Invalid request data",
        errors=details,
    )


async def http_error_handler(
    _: Request, error: StarletteHTTPException
) -> JSONResponse:
    message = error.detail if isinstance(error.detail, str) else "Request failed"
    return error_response(error.status_code, message, headers=error.headers)


async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
    route = request.scope.get("route")
    route_template = getattr(route, "path", "<unmatched>")
    logger.error(
        "Unhandled API error method=%s route=%s error_type=%s",
        request.method,
        route_template,
        type(error).__name__,
    )
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error"
    )


def error_response(
    status_code: int,
    message: str,
    *,
    headers: Mapping[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "success": False,
        "status": "error",
        "message": message,
        "error": {"message": message},
        **extra,
    }
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers=headers,
    )

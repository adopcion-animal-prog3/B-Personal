from typing import Literal

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    message: str


class ValidationIssue(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    status: Literal["error"] = "error"
    message: str
    error: ErrorDetail
    errors: list[ValidationIssue] | None = None


COMMON_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid request or business rule violation"},
    401: {"model": ErrorResponse, "description": "Authentication required or invalid"},
    403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Resource conflict"},
    500: {"model": ErrorResponse, "description": "Unexpected server error"},
    503: {"model": ErrorResponse, "description": "Database or service unavailable"},
}

from enum import Enum
from typing import Any


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ADOPTANTE = "ADOPTANTE"


class RequestStatus(str, Enum):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"


class BusinessRuleViolationError(Exception):
    pass


class InvalidRequestStatusError(BusinessRuleViolationError):
    pass


class InvalidRequestStatusTransitionError(BusinessRuleViolationError):
    pass


class MascotaNotAvailableError(BusinessRuleViolationError):
    pass


class InvalidMascotaAdoptionStateError(BusinessRuleViolationError):
    pass


class ResourceAccessDeniedError(BusinessRuleViolationError):
    pass


_ALLOWED_REQUEST_TRANSITIONS = {
    RequestStatus.PENDIENTE: {
        RequestStatus.PENDIENTE,
        RequestStatus.APROBADA,
        RequestStatus.RECHAZADA,
    },
    RequestStatus.APROBADA: {RequestStatus.APROBADA},
    RequestStatus.RECHAZADA: {RequestStatus.RECHAZADA},
}


def validate_request_status_transition(
    current_status: str, next_status: str
) -> RequestStatus:
    try:
        current = RequestStatus(current_status)
    except ValueError as error:
        raise InvalidRequestStatusError("Invalid current request status") from error
    try:
        next_value = RequestStatus(next_status)
    except ValueError as error:
        raise InvalidRequestStatusError("Invalid request status") from error
    if next_value not in _ALLOWED_REQUEST_TRANSITIONS[current]:
        raise InvalidRequestStatusTransitionError(
            f"Cannot change request status from {current.value} to {next_value.value}"
        )
    return next_value


def ensure_mascota_available(adoptada: object) -> None:
    if not isinstance(adoptada, bool):
        raise InvalidMascotaAdoptionStateError(
            "Mascota adoption status must be boolean"
        )
    if adoptada:
        raise MascotaNotAvailableError("Mascota is already adopted")


def require_request_access(user: dict[str, Any], requester_id: int) -> None:
    role = user.get("rol")
    if role == UserRole.ADMIN.value:
        return
    if role == UserRole.ADOPTANTE.value and user.get("id") == requester_id:
        return
    raise ResourceAccessDeniedError("Insufficient permissions")


def require_medical_history_access(user: dict[str, Any]) -> None:
    if user.get("rol") != UserRole.ADMIN.value:
        raise ResourceAccessDeniedError("Insufficient permissions")

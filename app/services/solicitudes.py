from typing import Any

from sqlalchemy.engine import Engine

from app.models.solicitud import SolicitudCreate, SolicitudUpdate
from app.repositories.mascotas import MascotaRepository
from app.repositories.solicitudes import SolicitudRepository
from app.services.mascotas import MascotaNotFoundError
from app.services.policies import (
    RequestStatus,
    ResourceAccessDeniedError,
    ensure_mascota_available,
    require_request_access,
    validate_request_status_transition,
)


class SolicitudNotFoundError(Exception):
    def __init__(self, solicitud_id: int) -> None:
        super().__init__(f"Solicitud {solicitud_id} not found")


class SolicitudService:
    def __init__(self, engine: Engine | None) -> None:
        self._repository = SolicitudRepository(engine)
        self._mascotas = MascotaRepository(engine)

    def list_solicitudes(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        if user.get("rol") == "ADMIN":
            return self._repository.list()
        usuario_id = user.get("id")
        if not isinstance(usuario_id, int) or isinstance(usuario_id, bool):
            raise ResourceAccessDeniedError("Authenticated user is invalid")
        require_request_access(user, usuario_id)
        return self._repository.list(usuario_id)

    def get_solicitud(
        self, solicitud_id: int, user: dict[str, Any]
    ) -> dict[str, Any]:
        solicitud = self._repository.get(solicitud_id)
        if solicitud is None:
            raise SolicitudNotFoundError(solicitud_id)
        require_request_access(user, solicitud["usuario_id"])
        return solicitud

    def create_solicitud(
        self, values: SolicitudCreate, user: dict[str, Any]
    ) -> dict[str, Any]:
        usuario_id = user.get("id")
        if not isinstance(usuario_id, int) or isinstance(usuario_id, bool):
            raise ResourceAccessDeniedError("Authenticated user is invalid")
        mascota = self._mascotas.get(values.mascota_id)
        if mascota is None:
            raise MascotaNotFoundError(values.mascota_id)
        ensure_mascota_available(mascota["adoptada"])
        return self._repository.create(
            {
                "usuario_id": usuario_id,
                "mascota_id": values.mascota_id,
                "estado": RequestStatus.PENDIENTE.value,
                "mensaje": values.mensaje,
            }
        )

    def update_solicitud(
        self,
        solicitud_id: int,
        changes: SolicitudUpdate,
    ) -> dict[str, Any]:
        existing = self._repository.get(solicitud_id)
        if existing is None:
            raise SolicitudNotFoundError(solicitud_id)
        next_status = validate_request_status_transition(
            existing["estado"], changes.estado.value
        )
        updated = self._repository.update(solicitud_id, next_status.value)
        if updated is None:
            raise SolicitudNotFoundError(solicitud_id)
        return updated

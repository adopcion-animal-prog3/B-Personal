from typing import Any

from sqlalchemy.engine import Engine

from app.models.historial import HistorialCreate, HistorialUpdate
from app.repositories.historial import HistorialRepository
from app.repositories.mascotas import MascotaRepository
from app.services.mascotas import MascotaNotFoundError
from app.services.policies import require_medical_history_access


class HistorialNotFoundError(Exception):
    def __init__(self, historial_id: int) -> None:
        super().__init__(f"Historial record {historial_id} not found")


class HistorialService:
    def __init__(self, engine: Engine | None) -> None:
        self._repository = HistorialRepository(engine)
        self._mascotas = MascotaRepository(engine)

    def list_for_mascota(
        self, mascota_id: int, user: dict[str, Any]
    ) -> list[dict[str, Any]]:
        require_medical_history_access(user)
        self._ensure_mascota_exists(mascota_id)
        return self._repository.list_for_mascota(mascota_id)

    def create(
        self,
        mascota_id: int,
        values: HistorialCreate,
        user: dict[str, Any],
    ) -> dict[str, Any]:
        require_medical_history_access(user)
        self._ensure_mascota_exists(mascota_id)
        fields = values.model_dump(exclude_none=True)
        return self._repository.create({"mascota_id": mascota_id, **fields})

    def update(
        self,
        historial_id: int,
        changes: HistorialUpdate,
        user: dict[str, Any],
    ) -> dict[str, Any]:
        require_medical_history_access(user)
        if self._repository.get(historial_id) is None:
            raise HistorialNotFoundError(historial_id)
        updated = self._repository.update(
            historial_id, changes.model_dump(exclude_unset=True)
        )
        if updated is None:
            raise HistorialNotFoundError(historial_id)
        return updated

    def delete(self, historial_id: int, user: dict[str, Any]) -> dict[str, Any]:
        require_medical_history_access(user)
        deleted = self._repository.delete(historial_id)
        if deleted is None:
            raise HistorialNotFoundError(historial_id)
        return deleted

    def _ensure_mascota_exists(self, mascota_id: int) -> None:
        if self._mascotas.get(mascota_id) is None:
            raise MascotaNotFoundError(mascota_id)

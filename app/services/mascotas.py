from typing import Any

from sqlalchemy import Engine

from app.models.mascota import MascotaCreate, MascotaUpdate
from app.repositories.mascotas import DatabaseUnavailableError, MascotaRepository


class MascotaNotFoundError(Exception):
    def __init__(self, mascota_id: int) -> None:
        super().__init__(f"Mascota {mascota_id} not found")


class MascotaService:
    def __init__(self, engine: Engine | None) -> None:
        self._repository = MascotaRepository(engine)

    def list_mascotas(self) -> list[dict[str, Any]]:
        return self._repository.list()

    def get_mascota(self, mascota_id: int) -> dict[str, Any]:
        mascota = self._repository.get(mascota_id)
        if mascota is None:
            raise MascotaNotFoundError(mascota_id)
        return mascota

    def create_mascota(self, mascota: MascotaCreate) -> dict[str, Any]:
        return self._repository.create(mascota.model_dump())

    def update_mascota(
        self, mascota_id: int, changes: MascotaUpdate
    ) -> dict[str, Any]:
        mascota = self._repository.update(
            mascota_id, changes.model_dump(exclude_unset=True)
        )
        if mascota is None:
            raise MascotaNotFoundError(mascota_id)
        return mascota

    def delete_mascota(self, mascota_id: int) -> None:
        if not self._repository.delete(mascota_id):
            raise MascotaNotFoundError(mascota_id)

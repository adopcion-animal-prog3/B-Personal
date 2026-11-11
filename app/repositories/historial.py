from collections.abc import Mapping
from typing import Any

from sqlalchemy import column, delete, insert, select, table, update
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func

from app.repositories.mascotas import DatabaseUnavailableError

_HISTORIAL = table(
    "historial_clinico",
    column("id"),
    column("mascota_id"),
    column("fecha_registro"),
    column("descripcion"),
    column("veterinario"),
    column("created_at"),
    column("updated_at"),
)


class HistorialRepository:
    def __init__(self, engine: Engine | None) -> None:
        self._engine = engine

    def list_for_mascota(self, mascota_id: int) -> list[dict[str, Any]]:
        query = (
            select(_HISTORIAL)
            .where(_HISTORIAL.c.mascota_id == mascota_id)
            .order_by(_HISTORIAL.c.fecha_registro.desc(), _HISTORIAL.c.id.desc())
        )
        with self._require_engine().connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [dict(row) for row in rows]

    def get(self, historial_id: int) -> dict[str, Any] | None:
        query = select(_HISTORIAL).where(_HISTORIAL.c.id == historial_id)
        with self._require_engine().connect() as connection:
            row = connection.execute(query).mappings().first()
        return dict(row) if row is not None else None

    def create(self, values: Mapping[str, Any]) -> dict[str, Any]:
        query = insert(_HISTORIAL).values(**dict(values)).returning(*_HISTORIAL.c)
        with self._require_engine().begin() as connection:
            row = connection.execute(query).mappings().one()
        return dict(row)

    def update(
        self, historial_id: int, values: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        allowed_fields = {"fecha_registro", "descripcion", "veterinario"}
        updates = dict(values)
        if not updates or set(updates) - allowed_fields:
            raise ValueError("Unsupported historial update fields")
        query = (
            update(_HISTORIAL)
            .where(_HISTORIAL.c.id == historial_id)
            .values(**updates, updated_at=func.now())
            .returning(*_HISTORIAL.c)
        )
        with self._require_engine().begin() as connection:
            row = connection.execute(query).mappings().first()
        return dict(row) if row is not None else None

    def delete(self, historial_id: int) -> dict[str, Any] | None:
        query = (
            delete(_HISTORIAL)
            .where(_HISTORIAL.c.id == historial_id)
            .returning(*_HISTORIAL.c)
        )
        with self._require_engine().begin() as connection:
            row = connection.execute(query).mappings().first()
        return dict(row) if row is not None else None

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise DatabaseUnavailableError("DATABASE_URL is not configured")
        return self._engine

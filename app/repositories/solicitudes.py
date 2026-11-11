from collections.abc import Mapping
from typing import Any

from sqlalchemy import column, insert, select, table, update
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func

from app.repositories.mascotas import DatabaseUnavailableError

_SOLICITUDES = table(
    "solicitudes_adopcion",
    column("id"),
    column("usuario_id"),
    column("mascota_id"),
    column("estado"),
    column("mensaje"),
    column("created_at"),
    column("updated_at"),
)


class SolicitudRepository:
    def __init__(self, engine: Engine | None) -> None:
        self._engine = engine

    def list(self, usuario_id: int | None = None) -> list[dict[str, Any]]:
        query = select(_SOLICITUDES).order_by(_SOLICITUDES.c.created_at.desc())
        if usuario_id is not None:
            query = query.where(_SOLICITUDES.c.usuario_id == usuario_id)
        with self._require_engine().connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [dict(row) for row in rows]

    def get(self, solicitud_id: int) -> dict[str, Any] | None:
        query = select(_SOLICITUDES).where(_SOLICITUDES.c.id == solicitud_id)
        with self._require_engine().connect() as connection:
            row = connection.execute(query).mappings().first()
        return dict(row) if row is not None else None

    def create(self, values: Mapping[str, Any]) -> dict[str, Any]:
        query = insert(_SOLICITUDES).values(**dict(values)).returning(*_SOLICITUDES.c)
        with self._require_engine().begin() as connection:
            row = connection.execute(query).mappings().one()
        return dict(row)

    def update(
        self, solicitud_id: int, estado: str
    ) -> dict[str, Any] | None:
        query = (
            update(_SOLICITUDES)
            .where(_SOLICITUDES.c.id == solicitud_id)
            .values(estado=estado, updated_at=func.now())
            .returning(*_SOLICITUDES.c)
        )
        with self._require_engine().begin() as connection:
            row = connection.execute(query).mappings().first()
        return dict(row) if row is not None else None

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise DatabaseUnavailableError("DATABASE_URL is not configured")
        return self._engine

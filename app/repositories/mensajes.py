from collections.abc import Mapping
from typing import Any

from sqlalchemy import and_, column, insert, or_, select, table, update
from sqlalchemy.engine import Engine

from app.repositories.mascotas import DatabaseUnavailableError

_MENSAJES = table(
    "mensajes",
    column("id"),
    column("remitente_id"),
    column("destinatario_id"),
    column("mascota_id"),
    column("contenido"),
    column("leido"),
    column("created_at"),
)
_USUARIOS = table("usuarios", column("id"), column("nombre"), column("rol"))


class MensajeRepository:
    """Acceso a la tabla compartida de mensajes y a los datos públicos de usuarios."""

    def __init__(self, engine: Engine | None) -> None:
        self._engine = engine

    def list_for_user(self, user_id: int) -> list[dict[str, Any]]:
        condition = or_(
            _MENSAJES.c.remitente_id == user_id,
            _MENSAJES.c.destinatario_id == user_id,
        )
        return self._all(select(_MENSAJES).where(condition).order_by(_MENSAJES.c.id))

    def conversation(self, user_id: int, other_id: int) -> list[dict[str, Any]]:
        condition = or_(
            and_(_MENSAJES.c.remitente_id == user_id, _MENSAJES.c.destinatario_id == other_id),
            and_(_MENSAJES.c.remitente_id == other_id, _MENSAJES.c.destinatario_id == user_id),
        )
        return self._all(select(_MENSAJES).where(condition).order_by(_MENSAJES.c.id))

    def mark_read(self, user_id: int, other_id: int) -> int:
        query = (
            update(_MENSAJES)
            .where(_MENSAJES.c.remitente_id == other_id)
            .where(_MENSAJES.c.destinatario_id == user_id)
            .where(_MENSAJES.c.leido.is_(False))
            .values(leido=True)
        )
        with self._require_engine().begin() as connection:
            return connection.execute(query).rowcount

    def create(self, values: Mapping[str, Any]) -> dict[str, Any]:
        query = insert(_MENSAJES).values(**dict(values)).returning(*_MENSAJES.c)
        with self._require_engine().begin() as connection:
            return dict(connection.execute(query).mappings().one())

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        rows = self._all(select(_USUARIOS).where(_USUARIOS.c.id == user_id))
        return rows[0] if rows else None

    def get_users(self, user_ids: set[int]) -> dict[int, dict[str, Any]]:
        if not user_ids:
            return {}
        rows = self._all(select(_USUARIOS).where(_USUARIOS.c.id.in_(user_ids)))
        return {row["id"]: row for row in rows}

    def _all(self, query: Any) -> list[dict[str, Any]]:
        with self._require_engine().connect() as connection:
            return [dict(row) for row in connection.execute(query).mappings().all()]

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise DatabaseUnavailableError("DATABASE_URL is not configured")
        return self._engine

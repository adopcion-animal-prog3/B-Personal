from datetime import datetime
from typing import Any

from sqlalchemy import column, insert, select, table, update
from sqlalchemy.engine import Engine

from app.repositories.mascotas import DatabaseUnavailableError

_CODIGOS = table(
    "codigos_verificacion",
    column("id"),
    column("usuario_id"),
    column("proposito"),
    column("codigo_hash"),
    column("intentos"),
    column("usado"),
    column("expira_en"),
    column("created_at"),
)
_USUARIOS = table("usuarios", column("id"), column("email_verificado"))


class VerificationRepository:
    """Persistencia de los códigos de verificación enviados por email."""

    def __init__(self, engine: Engine | None) -> None:
        self._engine = engine

    def active_code(self, user_id: int) -> dict[str, Any] | None:
        query = (
            select(_CODIGOS)
            .where(_CODIGOS.c.usuario_id == user_id, _CODIGOS.c.usado.is_(False))
            .order_by(_CODIGOS.c.id.desc())
            .limit(1)
        )
        with self._require_engine().connect() as connection:
            row = connection.execute(query).mappings().first()
        return dict(row) if row is not None else None

    def replace_code(
        self, user_id: int, proposito: str, codigo_hash: str, expira_en: datetime
    ) -> None:
        """Invalida los códigos pendientes del usuario y guarda uno nuevo."""
        with self._require_engine().begin() as connection:
            connection.execute(
                update(_CODIGOS)
                .where(_CODIGOS.c.usuario_id == user_id, _CODIGOS.c.usado.is_(False))
                .values(usado=True)
            )
            connection.execute(
                insert(_CODIGOS).values(
                    usuario_id=user_id,
                    proposito=proposito,
                    codigo_hash=codigo_hash,
                    intentos=0,
                    usado=False,
                    expira_en=expira_en,
                    created_at=datetime.now(expira_en.tzinfo),
                )
            )

    def register_failed_attempt(self, code_id: int, intentos: int) -> None:
        self._execute(update(_CODIGOS).where(_CODIGOS.c.id == code_id).values(intentos=intentos))

    def mark_used_and_verify(self, code_id: int, user_id: int) -> None:
        with self._require_engine().begin() as connection:
            connection.execute(update(_CODIGOS).where(_CODIGOS.c.id == code_id).values(usado=True))
            connection.execute(
                update(_USUARIOS).where(_USUARIOS.c.id == user_id).values(email_verificado=True)
            )

    def _execute(self, statement: Any) -> None:
        with self._require_engine().begin() as connection:
            connection.execute(statement)

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise DatabaseUnavailableError("DATABASE_URL is not configured")
        return self._engine

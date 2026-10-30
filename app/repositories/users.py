from typing import Any

from sqlalchemy import Engine, text

from app.repositories.mascotas import DatabaseUnavailableError

_USER_COLUMNS = "id, nombre, email, rol, password_hash"


class UserRepository:
    def __init__(self, engine: Engine | None) -> None:
        self._engine = engine

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        engine = self._require_engine()
        query = text(
            f"SELECT {_USER_COLUMNS} FROM usuarios WHERE LOWER(email) = :email"
        )
        with engine.connect() as connection:
            row = connection.execute(query, {"email": email}).mappings().first()
        return dict(row) if row is not None else None

    def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        engine = self._require_engine()
        query = text(f"SELECT {_USER_COLUMNS} FROM usuarios WHERE id = :user_id")
        with engine.connect() as connection:
            row = connection.execute(query, {"user_id": user_id}).mappings().first()
        return dict(row) if row is not None else None

    def create(
        self, nombre: str, email: str, password_hash: str
    ) -> dict[str, Any]:
        engine = self._require_engine()
        query = text(
            "INSERT INTO usuarios (nombre, email, password_hash) "
            "VALUES (:nombre, :email, :password_hash) "
            f"RETURNING {_USER_COLUMNS}"
        )
        with engine.begin() as connection:
            row = connection.execute(
                query,
                {
                    "nombre": nombre,
                    "email": email,
                    "password_hash": password_hash,
                },
            ).mappings().one()
        return dict(row)

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise DatabaseUnavailableError("DATABASE_URL is not configured")
        return self._engine

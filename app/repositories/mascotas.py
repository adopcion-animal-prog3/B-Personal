from collections.abc import Mapping
from typing import Any

from sqlalchemy import Engine, text


class DatabaseUnavailableError(Exception):
    pass


_MASCOTA_COLUMNS = (
    "id, nombre, especie, raza, edad, sexo, descripcion, adoptada, creado_por, created_at"
)
_UPDATE_COLUMNS = (
    "nombre",
    "especie",
    "raza",
    "edad",
    "sexo",
    "descripcion",
    "adoptada",
)


class MascotaRepository:
    def __init__(self, engine: Engine | None) -> None:
        self._engine = engine

    def list(self) -> list[dict[str, Any]]:
        engine = self._require_engine()
        query = text(f"SELECT {_MASCOTA_COLUMNS} FROM mascotas ORDER BY id")
        with engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [dict(row) for row in rows]

    def get(self, mascota_id: int) -> dict[str, Any] | None:
        engine = self._require_engine()
        query = text(
            f"SELECT {_MASCOTA_COLUMNS} FROM mascotas WHERE id = :mascota_id"
        )
        with engine.connect() as connection:
            row = connection.execute(query, {"mascota_id": mascota_id}).mappings().first()
        return dict(row) if row is not None else None

    def create(self, values: Mapping[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        query = text(
            "INSERT INTO mascotas "
            "(nombre, especie, raza, edad, sexo, descripcion, adoptada, creado_por) "
            "VALUES (:nombre, :especie, :raza, :edad, :sexo, :descripcion, :adoptada, :creado_por) "
            f"RETURNING {_MASCOTA_COLUMNS}"
        )
        with engine.begin() as connection:
            row = connection.execute(query, dict(values)).mappings().one()
        return dict(row)

    def update(
        self, mascota_id: int, values: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        unsupported_fields = set(values) - set(_UPDATE_COLUMNS)
        if unsupported_fields:
            raise ValueError("Unsupported mascota update field")
        updates = {
            column: values[column] for column in _UPDATE_COLUMNS if column in values
        }
        if not updates:
            return self.get(mascota_id)

        engine = self._require_engine()
        assignments = ", ".join(
            f"{column} = :{column}" for column in updates
        )
        query = text(
            f"UPDATE mascotas SET {assignments} WHERE id = :mascota_id "
            f"RETURNING {_MASCOTA_COLUMNS}"
        )
        parameters = {**updates, "mascota_id": mascota_id}
        with engine.begin() as connection:
            row = connection.execute(query, parameters).mappings().first()
        return dict(row) if row is not None else None

    def delete(self, mascota_id: int) -> bool:
        engine = self._require_engine()
        query = text("DELETE FROM mascotas WHERE id = :mascota_id RETURNING id")
        with engine.begin() as connection:
            deleted_id = connection.execute(
                query, {"mascota_id": mascota_id}
            ).scalar_one_or_none()
        return deleted_id is not None

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise DatabaseUnavailableError("DATABASE_URL is not configured")
        return self._engine

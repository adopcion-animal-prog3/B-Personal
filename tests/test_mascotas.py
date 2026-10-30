import unittest
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import create_app
from app.models.mascota import MascotaCreate
from app.repositories.mascotas import MascotaRepository
from app.services.mascotas import (
    DatabaseUnavailableError,
    MascotaNotFoundError,
    MascotaService,
)


def mascota_row(mascota_id: int = 1, **overrides: Any) -> dict[str, Any]:
    return {
        "id": mascota_id,
        "nombre": "Luna",
        "especie": "Perro",
        "raza": "Labrador",
        "edad": 2,
        "sexo": "F",
        "descripcion": "Sociable",
        "adoptada": False,
        "creado_por": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        **overrides,
    }


class FakeMascotaRepository:
    def __init__(self) -> None:
        self.rows: dict[int, dict[str, Any]] = {1: mascota_row()}

    def list(self) -> list[dict[str, Any]]:
        return list(self.rows.values())

    def get(self, mascota_id: int) -> dict[str, Any] | None:
        return self.rows.get(mascota_id)

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        row = mascota_row(2, **values)
        self.rows[2] = row
        return row

    def update(
        self, mascota_id: int, values: dict[str, Any]
    ) -> dict[str, Any] | None:
        row = self.rows.get(mascota_id)
        if row is None:
            return None
        row.update(values)
        return row

    def delete(self, mascota_id: int) -> bool:
        return self.rows.pop(mascota_id, None) is not None


class MascotaEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        repository = FakeMascotaRepository()
        self.app.state.mascota_service = MascotaService.__new__(MascotaService)
        self.app.state.mascota_service._repository = repository
        self.repository = repository
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()

    def test_list_and_get_mascotas(self) -> None:
        listed = self.client.get("/api/mascotas")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)
        self.assertEqual(listed.json()["data"][0]["id"], 1)

        fetched = self.client.get("/api/mascotas/1")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["data"]["nombre"], "Luna")

    def test_missing_and_invalid_ids(self) -> None:
        self.assertEqual(self.client.get("/api/mascotas/999").status_code, 404)
        self.assertEqual(self.client.get("/api/mascotas/0").status_code, 400)
        self.assertEqual(
            self.client.get("/api/mascotas/9223372036854775808").status_code, 400
        )
        self.assertEqual(self.client.put("/api/mascotas/999", json={}).status_code, 404)
        self.assertEqual(self.client.delete("/api/mascotas/999").status_code, 404)

    def test_create_and_update(self) -> None:
        created = self.client.post(
            "/api/mascotas",
            json={"nombre": "Mora", "especie": "Gato", "edad": 0},
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["data"]["nombre"], "Mora")
        self.assertFalse(created.json()["data"]["adoptada"])

        updated = self.client.put(
            "/api/mascotas/1", json={"nombre": "Luna nueva", "raza": None}
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["nombre"], "Luna nueva")
        self.assertIsNone(updated.json()["data"]["raza"])

    def test_invalid_payloads_are_rejected_without_writing(self) -> None:
        for payload in (
            {"especie": "Perro"},
            {"nombre": "Mora", "especie": "Gato", "edad": -1},
            {"nombre": "Mora", "especie": "Gato", "sexo": "X"},
            {"nombre": "Mora", "especie": "Gato", "adoptada": "false"},
            {"nombre": "Mora", "especie": "Gato", "extra": "not allowed"},
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/api/mascotas", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["success"])
        self.assertEqual(len(self.repository.rows), 1)

        response = self.client.put("/api/mascotas/1", json={"nombre": None})
        self.assertEqual(response.status_code, 400)

    def test_delete_returns_empty_204_and_removes_record(self) -> None:
        response = self.client.delete("/api/mascotas/1")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.get("/api/mascotas/1").status_code, 404)

    def test_database_unavailable_returns_503(self) -> None:
        self.app.state.mascota_service = MascotaService(None)
        response = self.client.get("/api/mascotas")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["success"])


class MascotaRepositoryTests(unittest.TestCase):
    def test_crud_persists_values_with_sqlite_repository(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE TABLE mascotas ("
                        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                        "nombre VARCHAR(150) NOT NULL, especie VARCHAR(100) NOT NULL, "
                        "raza VARCHAR(120), edad INTEGER, sexo VARCHAR(20), "
                        "descripcion TEXT, adoptada BOOLEAN NOT NULL DEFAULT FALSE, "
                        "creado_por INTEGER, "
                        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                    )
                )
            repository = MascotaRepository(engine)
            created = repository.create(
                MascotaCreate(nombre="Mora' OR 1=1 --", especie="Gato").model_dump()
            )
            self.assertEqual(created["nombre"], "Mora' OR 1=1 --")
            self.assertEqual(len(repository.list()), 1)

            updated = repository.update(created["id"], {"edad": 4})
            self.assertEqual(updated["edad"], 4)
            self.assertEqual(repository.get(created["id"])["edad"], 4)
            with self.assertRaises(ValueError):
                repository.update(created["id"], {"untrusted_column": "ignored"})
            self.assertTrue(repository.delete(created["id"]))
            self.assertIsNone(repository.get(created["id"]))
            self.assertFalse(repository.delete(created["id"]))
        finally:
            engine.dispose()

    def test_service_raises_not_found_for_missing_id(self) -> None:
        repository = FakeMascotaRepository()
        service = MascotaService(None)
        service._repository = repository
        with self.assertRaises(MascotaNotFoundError):
            service.get_mascota(99)

    def test_unconfigured_database_is_explicit(self) -> None:
        with self.assertRaises(DatabaseUnavailableError):
            MascotaRepository(None).list()


if __name__ == "__main__":
    unittest.main()

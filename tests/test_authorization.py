import unittest
from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app
from app.routes.auth import get_current_user
from app.services.policies import (
    InvalidMascotaAdoptionStateError,
    InvalidRequestStatusError,
    InvalidRequestStatusTransitionError,
    MascotaNotAvailableError,
    RequestStatus,
    ResourceAccessDeniedError,
    ensure_mascota_available,
    require_medical_history_access,
    require_request_access,
    validate_request_status_transition,
)


def mascota_row(mascota_id: int = 1, **overrides: Any) -> dict[str, Any]:
    return {
        "id": mascota_id,
        "nombre": "Luna",
        "especie": "Perro",
        "raza": None,
        "edad": 2,
        "sexo": "F",
        "descripcion": None,
        "adoptada": False,
        "creado_por": None,
        "created_at": "2026-01-01T00:00:00Z",
        **overrides,
    }


class FakeMascotaService:
    def __init__(self) -> None:
        self.rows = {1: mascota_row()}

    def list_mascotas(self) -> list[dict[str, Any]]:
        return list(self.rows.values())

    def get_mascota(self, mascota_id: int) -> dict[str, Any]:
        return self.rows[mascota_id]

    def create_mascota(self, values: Any) -> dict[str, Any]:
        row = mascota_row(2, **values.model_dump())
        self.rows[2] = row
        return row

    def update_mascota(self, mascota_id: int, changes: Any) -> dict[str, Any]:
        self.rows[mascota_id].update(changes.model_dump(exclude_unset=True))
        return self.rows[mascota_id]

    def delete_mascota(self, mascota_id: int) -> None:
        del self.rows[mascota_id]


class MascotaAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.state.mascota_service = FakeMascotaService()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()

    def set_user(self, role: str) -> None:
        self.app.dependency_overrides[get_current_user] = lambda: {
            "id": 1,
            "rol": role,
        }

    def test_admin_can_create_update_and_delete_mascotas(self) -> None:
        self.set_user("ADMIN")

        created = self.client.post(
            "/api/mascotas",
            json={"nombre": "Mora", "especie": "Gato"},
        )
        self.assertEqual(created.status_code, 201)

        updated = self.client.put(
            "/api/mascotas/1",
            json={"nombre": "Luna nueva"},
        )
        self.assertEqual(updated.status_code, 200)

        deleted = self.client.delete("/api/mascotas/1")
        self.assertEqual(deleted.status_code, 204)

    def test_adoptante_cannot_create_update_or_delete_mascotas(self) -> None:
        self.set_user("ADOPTANTE")

        responses = (
            self.client.post(
                "/api/mascotas",
                json={"nombre": "Mora", "especie": "Gato"},
            ),
            self.client.put("/api/mascotas/1", json={"nombre": "Luna nueva"}),
            self.client.delete("/api/mascotas/1"),
        )
        self.assertEqual([response.status_code for response in responses], [403] * 3)

    def test_missing_token_is_401_but_public_reads_remain_available(self) -> None:
        write_response = self.client.post(
            "/api/mascotas",
            json={"nombre": "Mora", "especie": "Gato"},
        )
        read_response = self.client.get("/api/mascotas")

        self.assertEqual(write_response.status_code, 401)
        self.assertEqual(read_response.status_code, 200)


class BusinessPolicyTests(unittest.TestCase):
    def test_request_statuses_and_transitions(self) -> None:
        self.assertEqual(
            validate_request_status_transition("PENDIENTE", "APROBADA"),
            RequestStatus.APROBADA,
        )
        self.assertEqual(
            validate_request_status_transition("PENDIENTE", "RECHAZADA"),
            RequestStatus.RECHAZADA,
        )
        self.assertEqual(
            validate_request_status_transition("APROBADA", "APROBADA"),
            RequestStatus.APROBADA,
        )
        with self.assertRaises(InvalidRequestStatusTransitionError):
            validate_request_status_transition("APROBADA", "PENDIENTE")
        with self.assertRaises(InvalidRequestStatusTransitionError):
            validate_request_status_transition("RECHAZADA", "APROBADA")
        with self.assertRaises(InvalidRequestStatusError):
            validate_request_status_transition("PENDIENTE", "CANCELADA")

    def test_adoption_state_must_be_boolean_and_available(self) -> None:
        ensure_mascota_available(False)
        with self.assertRaises(MascotaNotAvailableError):
            ensure_mascota_available(True)
        with self.assertRaises(InvalidMascotaAdoptionStateError):
            ensure_mascota_available("false")

    def test_request_access_is_limited_to_admin_or_requester(self) -> None:
        require_request_access({"id": 7, "rol": "ADMIN"}, requester_id=9)
        require_request_access({"id": 9, "rol": "ADOPTANTE"}, requester_id=9)
        with self.assertRaises(ResourceAccessDeniedError):
            require_request_access({"id": 7, "rol": "ADOPTANTE"}, requester_id=9)
        with self.assertRaises(ResourceAccessDeniedError):
            require_request_access({"id": 9, "rol": "UNKNOWN"}, requester_id=9)

    def test_medical_history_access_is_admin_only(self) -> None:
        require_medical_history_access({"id": 1, "rol": "ADMIN"})
        with self.assertRaises(ResourceAccessDeniedError):
            require_medical_history_access({"id": 1, "rol": "ADOPTANTE"})


if __name__ == "__main__":
    unittest.main()

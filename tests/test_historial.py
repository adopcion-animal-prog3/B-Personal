from support import AdoptionApiTestCase
from sqlalchemy import text


class HistorialEndpointTests(AdoptionApiTestCase):
    def test_create_and_list_history_for_existing_mascota(self) -> None:
        self.set_user(1, "ADMIN")
        created = self.client.post(
            "/api/mascotas/1/historial",
            json={
                "fecha_registro": "2026-04-03T10:30:00Z",
                "descripcion": "Vacunación anual",
                "veterinario": "Dra. Torres",
            },
        )
        self.assertEqual(created.status_code, 201)
        record = created.json()["data"]
        self.assertEqual(record["mascota_id"], 1)
        self.assertEqual(record["descripcion"], "Vacunación anual")

        listed = self.client.get("/api/mascotas/1/historial")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)
        self.assertEqual(listed.json()["data"][0]["id"], record["id"])
        with self.engine.connect() as connection:
            persisted = connection.execute(
                text(
                    "SELECT mascota_id, descripcion, veterinario "
                    "FROM historial_clinico WHERE id = :id"
                ),
                {"id": record["id"]},
            ).mappings().one()
        self.assertEqual(persisted["mascota_id"], 1)
        self.assertEqual(persisted["descripcion"], "Vacunación anual")
        self.assertEqual(persisted["veterinario"], "Dra. Torres")

    def test_history_requires_existing_mascota_and_valid_data(self) -> None:
        self.set_user(1, "ADMIN")
        self.assertEqual(
            self.client.get("/api/mascotas/999/historial").status_code, 404
        )
        self.assertEqual(
            self.client.post(
                "/api/mascotas/999/historial",
                json={"descripcion": "Consulta"},
            ).status_code,
            404,
        )
        for payload in (
            {},
            {"descripcion": ""},
            {"descripcion": " ", "veterinario": "Dra"},
            {"descripcion": "Consulta", "mascota_id": 2},
            {"descripcion": "Consulta", "fecha_registro": "invalid"},
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/api/mascotas/1/historial", json=payload)
                self.assertEqual(response.status_code, 400)

    def test_history_write_and_read_access_is_admin_only(self) -> None:
        self.assertEqual(
            self.client.get("/api/mascotas/1/historial").status_code, 403
        )
        self.assertEqual(
            self.client.post(
                "/api/mascotas/1/historial",
                json={"descripcion": "Consulta"},
            ).status_code,
            403,
        )
        self.set_user(1, "ADMIN")
        record = self.client.post(
            "/api/mascotas/1/historial", json={"descripcion": "Consulta"}
        ).json()["data"]
        self.set_user(2, "ADOPTANTE")
        record_url = f"/api/historial/{record['id']}"
        self.assertEqual(
            self.client.put(record_url, json={"descripcion": "Actualizado"}).status_code,
            403,
        )
        self.assertEqual(self.client.delete(record_url).status_code, 403)

    def test_update_changes_record_and_rejects_invalid_or_missing_data(self) -> None:
        self.set_user(1, "ADMIN")
        record = self.client.post(
            "/api/mascotas/1/historial",
            json={"descripcion": "Consulta inicial", "veterinario": "Dra. A"},
        ).json()["data"]
        record_url = f"/api/historial/{record['id']}"
        updated = self.client.put(
            record_url,
            json={"descripcion": "Consulta de control", "veterinario": None},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["descripcion"], "Consulta de control")
        self.assertIsNone(updated.json()["data"]["veterinario"])
        self.assertEqual(
            self.client.put(record_url, json={"fecha_registro": None}).status_code,
            400,
        )
        self.assertEqual(self.client.put(record_url, json={}).status_code, 400)
        self.assertEqual(
            self.client.put("/api/historial/999", json={"descripcion": "No existe"}).status_code,
            404,
        )

    def test_delete_is_persistent_and_returns_not_found_afterward(self) -> None:
        self.set_user(1, "ADMIN")
        record = self.client.post(
            "/api/mascotas/1/historial", json={"descripcion": "Consulta"}
        ).json()["data"]
        record_url = f"/api/historial/{record['id']}"

        deleted = self.client.delete(record_url)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            deleted.json()["data"]["message"],
            "Historial clinico deleted successfully",
        )
        self.assertEqual(deleted.json()["data"]["data"]["id"], record["id"])
        self.assertEqual(self.client.delete(record_url).status_code, 404)
        with self.engine.connect() as connection:
            remaining = connection.execute(
                text("SELECT COUNT(*) FROM historial_clinico WHERE id = :id"),
                {"id": record["id"]},
            ).scalar_one()
        self.assertEqual(remaining, 0)

    def test_authentication_is_required_for_history_reads(self) -> None:
        self.app.dependency_overrides.clear()
        self.assertEqual(
            self.client.get("/api/mascotas/1/historial").status_code, 401
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

from support import AdoptionApiTestCase
from sqlalchemy import text


class SolicitudEndpointTests(AdoptionApiTestCase):
    def test_create_links_authenticated_user_and_persists_request(self) -> None:
        response = self.client.post(
            "/api/solicitudes",
            json={"mascota_id": 1, "mensaje": "Quisiera adoptar a Luna"},
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["usuario_id"], 2)
        self.assertEqual(data["mascota_id"], 1)
        self.assertEqual(data["estado"], "PENDIENTE")
        self.assertEqual(data["mensaje"], "Quisiera adoptar a Luna")
        with self.engine.connect() as connection:
            persisted = connection.execute(
                text(
                    "SELECT usuario_id, mascota_id, estado, mensaje "
                    "FROM solicitudes_adopcion WHERE id = :id"
                ),
                {"id": data["id"]},
            ).mappings().one()
        self.assertEqual(persisted["usuario_id"], 2)
        self.assertEqual(persisted["mascota_id"], 1)

    def test_create_rejects_missing_or_adopted_mascotas_and_invalid_payloads(
        self,
    ) -> None:
        missing = self.client.post("/api/solicitudes", json={"mascota_id": 99})
        adopted = self.client.post("/api/solicitudes", json={"mascota_id": 2})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(adopted.status_code, 400)

        for payload in (
            {},
            {"mascota_id": 0},
            {"mascota_id": "1"},
            {"mascota_id": 1, "estado": "APROBADA"},
            {"mascota_id": 1, "mensaje": 42},
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/api/solicitudes", json=payload)
                self.assertEqual(response.status_code, 400)

    def test_list_filters_adoptantes_and_admin_sees_all(self) -> None:
        self.client.post("/api/solicitudes", json={"mascota_id": 1})
        self.set_user(3)
        self.client.post("/api/solicitudes", json={"mascota_id": 1})

        own_requests = self.client.get("/api/solicitudes")
        self.assertEqual(own_requests.status_code, 200)
        self.assertEqual(own_requests.json()["count"], 1)
        self.assertEqual(own_requests.json()["data"][0]["usuario_id"], 3)

        self.set_user(1, "ADMIN")
        all_requests = self.client.get("/api/solicitudes")
        self.assertEqual(all_requests.json()["count"], 2)

    def test_get_request_enforces_ownership_and_returns_not_found(self) -> None:
        created = self.client.post(
            "/api/solicitudes", json={"mascota_id": 1}
        ).json()["data"]
        self.assertEqual(
            self.client.get(f"/api/solicitudes/{created['id']}").status_code, 200
        )

        self.set_user(3)
        self.assertEqual(
            self.client.get(f"/api/solicitudes/{created['id']}").status_code, 403
        )
        self.assertEqual(self.client.get("/api/solicitudes/999").status_code, 404)
        self.assertEqual(self.client.get("/api/solicitudes/0").status_code, 400)

    def test_only_admin_can_update_and_terminal_states_cannot_change(self) -> None:
        created = self.client.post(
            "/api/solicitudes", json={"mascota_id": 1}
        ).json()["data"]
        request_url = f"/api/solicitudes/{created['id']}"
        self.assertEqual(
            self.client.put(request_url, json={"estado": "APROBADA"}).status_code,
            403,
        )

        self.set_user(1, "ADMIN")
        approved = self.client.put(request_url, json={"estado": "APROBADA"})
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["data"]["estado"], "APROBADA")
        self.assertEqual(
            self.client.put(request_url, json={"estado": "RECHAZADA"}).status_code,
            400,
        )
        self.assertEqual(
            self.client.put("/api/solicitudes/999", json={"estado": "PENDIENTE"}).status_code,
            404,
        )
        self.assertEqual(
            self.client.put(request_url, json={"estado": "UNKNOWN"}).status_code,
            400,
        )

    def test_authentication_is_required_for_request_reads(self) -> None:
        self.app.dependency_overrides.clear()
        self.assertEqual(self.client.get("/api/solicitudes").status_code, 401)


if __name__ == "__main__":
    import unittest

    unittest.main()

from sqlalchemy import text

from app.services.mensajes import MensajeService, build_conversaciones
from tests.support import AdoptionApiTestCase


class MensajesApiTests(AdoptionApiTestCase):
    """El usuario por defecto es el adoptante 2; el usuario 1 es la cuenta profesional."""

    def setUp(self) -> None:
        super().setUp()
        self.app.state.mensaje_service = MensajeService(self.engine)

    def send(self, **overrides: object):
        payload = {"destinatario_id": 1, "mascota_id": 1, "contenido": "Hola", **overrides}
        return self.client.post("/api/mensajes", json=payload)

    def test_sends_message_using_the_authenticated_sender(self) -> None:
        response = self.send(contenido="  ¿Puedo conocer a Luna?  ")

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["remitente_id"], 2)
        self.assertEqual(data["destinatario_id"], 1)
        self.assertEqual(data["contenido"], "¿Puedo conocer a Luna?")
        self.assertFalse(data["leido"])

    def test_rejects_sender_override_and_invalid_payloads(self) -> None:
        cases = [
            {"remitente_id": 3},
            {"contenido": "   "},
            {"contenido": "a" * 2001},
            {"destinatario_id": "1"},
            {"mascota_id": 0},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(self.send(**overrides).status_code, 400)

    def test_rejects_messages_to_self_or_missing_resources(self) -> None:
        self.assertEqual(self.send(destinatario_id=2).status_code, 400)
        self.assertEqual(self.send(destinatario_id=99).status_code, 404)
        self.assertEqual(self.send(mascota_id=99).status_code, 404)

    def test_lists_conversations_with_unread_counts(self) -> None:
        self.send(contenido="Primero")
        self.set_user(1, "ADMIN")
        self.send(destinatario_id=2, contenido="Respuesta")
        self.send(destinatario_id=3, contenido="Otro adoptante")

        response = self.client.get("/api/mensajes/conversaciones")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual([c["usuario"]["id"] for c in body["data"]], [3, 2])
        self.assertEqual(body["data"][1]["no_leidos"], 1)
        self.assertEqual(body["data"][1]["usuario"]["nombre"], "Adoptante")

    def test_returns_thread_and_marks_received_messages_as_read(self) -> None:
        self.send(contenido="Uno")
        self.send(contenido="Dos")
        self.set_user(1, "ADMIN")

        thread = self.client.get("/api/mensajes/conversaciones/2")
        marked = self.client.put("/api/mensajes/conversaciones/2/leidos")
        again = self.client.put("/api/mensajes/conversaciones/2/leidos")

        self.assertEqual(thread.status_code, 200)
        self.assertEqual([m["contenido"] for m in thread.json()["data"]["mensajes"]], ["Uno", "Dos"])
        self.assertEqual(thread.json()["data"]["usuario"]["rol"], "ADOPTANTE")
        self.assertEqual(marked.json()["data"]["actualizados"], 2)
        self.assertEqual(again.json()["data"]["actualizados"], 0)

    def test_conversation_with_unknown_user_returns_404(self) -> None:
        self.assertEqual(self.client.get("/api/mensajes/conversaciones/99").status_code, 404)
        self.assertEqual(self.client.put("/api/mensajes/conversaciones/99/leidos").status_code, 404)

    def test_requires_authentication(self) -> None:
        self.user = None
        self.app.dependency_overrides.clear()

        self.assertEqual(self.client.get("/api/mensajes/conversaciones").status_code, 401)

    def test_other_users_messages_are_not_visible(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO mensajes (remitente_id, destinatario_id, contenido) "
                    "VALUES (3, 1, 'Privado')"
                )
            )

        response = self.client.get("/api/mensajes/conversaciones")

        self.assertEqual(response.json()["data"], [])


class BuildConversacionesTests(AdoptionApiTestCase):
    def test_skips_conversations_with_unknown_users(self) -> None:
        mensajes = [
            {"id": 1, "remitente_id": 5, "destinatario_id": 2, "leido": False},
        ]

        self.assertEqual(build_conversaciones(mensajes, 2, {}), [])

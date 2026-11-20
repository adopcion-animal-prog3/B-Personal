import re
import secrets
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.services.auth import AuthService
from app.services.mailer import Mailer

EMAIL = "ana@example.com"


class VerificationFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        with self.engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre VARCHAR(150), "
                "email VARCHAR(255) UNIQUE, password_hash VARCHAR(255), rol VARCHAR(20) NOT NULL "
                "DEFAULT 'ADOPTANTE', email_verificado BOOLEAN NOT NULL DEFAULT 0, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            ))
            connection.execute(text(
                "CREATE TABLE codigos_verificacion (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "usuario_id INTEGER, proposito VARCHAR(20), codigo_hash VARCHAR(64), "
                "intentos INTEGER DEFAULT 0, usado BOOLEAN DEFAULT 0, expira_en TIMESTAMP, "
                "created_at TIMESTAMP)"
            ))
        settings = Settings(jwt_secret=secrets.token_urlsafe(32), mail_mode="memory")
        self.app = create_app(settings)
        self.service = AuthService(self.engine, settings)
        self.app.state.auth_service = self.service
        self.client = TestClient(self.app)
        payload = {"nombre": "Ana", "email": EMAIL, "password": "clave segura 123"}
        self.assertEqual(self.client.post("/api/auth/register", json=payload).status_code, 201)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def code(self) -> str:
        return re.search(r"\b(\d{6})\b", self.service.mailer.outbox[-1]["text"]).group(1)

    def verify(self, codigo: str):
        return self.client.post("/api/auth/verify", json={"email": EMAIL, "codigo": codigo})

    def wrong(self) -> str:
        return f"{(int(self.code()) + 1) % 1_000_000:06d}"

    def set_code_column(self, column: str, value: object) -> None:
        with self.engine.begin() as connection:
            connection.execute(text(f"UPDATE codigos_verificacion SET {column} = :v"), {"v": value})

    def test_registration_code_verifies_email_and_cannot_be_reused(self) -> None:
        code = self.code()
        response = self.verify(code)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["user"]["email"], EMAIL)
        with self.engine.connect() as connection:
            verified = connection.execute(text("SELECT email_verificado FROM usuarios")).scalar_one()
        self.assertTrue(verified)
        self.assertEqual(self.verify(code).status_code, 400)

    def test_wrong_codes_are_limited_to_five_attempts(self) -> None:
        for _ in range(5):
            self.assertEqual(self.verify(self.wrong()).status_code, 400)
        self.assertEqual(self.verify(self.code()).status_code, 429)

    def test_expired_codes_are_rejected(self) -> None:
        self.set_code_column("expira_en", datetime.now(timezone.utc) - timedelta(minutes=1))
        response = self.verify(self.code())
        self.assertEqual(response.status_code, 400)
        self.assertIn("expired", response.json()["message"])

    def test_resend_waits_a_minute_and_then_issues_a_new_code(self) -> None:
        resend = lambda: self.client.post("/api/auth/resend-code", json={"email": EMAIL})  # noqa: E731
        self.assertEqual(resend().status_code, 429)

        self.set_code_column("created_at", datetime.now(timezone.utc) - timedelta(minutes=2))
        old_code = self.code()
        self.assertEqual(resend().status_code, 200)
        self.assertEqual(len(self.service.mailer.outbox), 2)
        if self.code() != old_code:
            self.assertEqual(self.verify(old_code).status_code, 400)
        self.assertEqual(self.verify(self.code()).status_code, 200)

    def test_resend_and_verify_do_not_reveal_unknown_or_professional_accounts(self) -> None:
        unknown = self.client.post("/api/auth/resend-code", json={"email": "nadie@example.com"})
        self.assertEqual(unknown.status_code, 200)
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE usuarios SET rol = 'ADMIN'"))
        self.assertEqual(self.verify(self.code()).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/verify", json={"email": EMAIL, "codigo": "12a"}).status_code, 400)


class MailerTests(unittest.TestCase):
    def test_log_mode_is_default_without_smtp(self) -> None:
        mailer = Mailer(Settings())
        with self.assertLogs("app.services.mailer", level="INFO") as logs:
            mailer.send("a@example.com", "Asunto", "Código 123456", "<p>x</p>")
        self.assertIn("Código 123456", logs.output[0])

    def test_smtp_mode_sends_with_starttls_and_credentials(self) -> None:
        settings = Settings(
            smtp_host="smtp.example.test", smtp_port=587, smtp_user="user",
            smtp_password="app-password", smtp_starttls=True,
        )
        with mock.patch("app.services.mailer.smtplib.SMTP") as smtp:
            Mailer(settings).send("a@example.com", "Asunto", "texto", "<p>html</p>")
        server = smtp.return_value.__enter__.return_value
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("user", "app-password")
        message = server.send_message.call_args.args[0]
        self.assertEqual(message["To"], "a@example.com")
        self.assertEqual(settings.resolved_mail_mode(), "smtp")

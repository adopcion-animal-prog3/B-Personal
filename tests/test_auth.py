import secrets
import unittest
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.services.auth import AuthService


class AuthEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE usuarios ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "nombre VARCHAR(150) NOT NULL, "
                    "email VARCHAR(255) NOT NULL UNIQUE, "
                    "password_hash VARCHAR(255) NOT NULL, "
                    "rol VARCHAR(20) NOT NULL DEFAULT 'ADOPTANTE' "
                    "CHECK (rol IN ('ADMIN', 'ADOPTANTE')), "
                    "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                )
            )
        self.jwt_secret = secrets.token_urlsafe(32)
        settings = Settings(jwt_secret=self.jwt_secret)
        self.app = create_app(settings)
        self.app.state.auth_service = AuthService(self.engine, settings)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def register(self, **overrides: str):
        payload = {
            "nombre": "Ada Lovelace",
            "email": "ada@example.com",
            "password": "secure password 123",
            **overrides,
        }
        return self.client.post("/api/auth/register", json=payload)

    def login(self, **overrides: str):
        payload = {
            "email": "ada@example.com",
            "password": "secure password 123",
            **overrides,
        }
        return self.client.post("/api/auth/login", json=payload)

    def test_register_stores_password_hash_and_default_role(self) -> None:
        response = self.register(email=" ADA@Example.com ")

        self.assertEqual(response.status_code, 201)
        user = response.json()["data"]
        self.assertEqual(user["email"], "ada@example.com")
        self.assertEqual(user["rol"], "ADOPTANTE")
        self.assertNotIn("password", response.text)
        self.assertNotIn("password_hash", response.text)

        with self.engine.connect() as connection:
            stored = connection.execute(
                text(
                    "SELECT password_hash, rol FROM usuarios "
                    "WHERE email = :email"
                ),
                {"email": "ada@example.com"},
            ).one()
        self.assertTrue(stored.password_hash.startswith("$2"))
        self.assertTrue(
            bcrypt.checkpw(
                b"secure password 123", stored.password_hash.encode("ascii")
            )
        )
        self.assertEqual(stored.rol, "ADOPTANTE")

    def test_duplicate_email_is_rejected_case_insensitively(self) -> None:
        self.assertEqual(self.register().status_code, 201)

        duplicate = self.register(email="ADA@example.com")

        self.assertEqual(duplicate.status_code, 409)

    def test_registration_rejects_invalid_input_and_privileged_role(self) -> None:
        for payload in (
            {"nombre": "Ada", "email": "not-an-email", "password": "valid pass 123"},
            {"nombre": "Ada", "email": "ada@example.com", "password": "short"},
            {
                "nombre": "Ada",
                "email": "ada@example.com",
                "password": "valid pass 123",
                "rol": "ADMIN",
            },
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/api/auth/register", json=payload)
                self.assertEqual(response.status_code, 400)
        with self.engine.connect() as connection:
            count = connection.execute(
                text("SELECT COUNT(*) FROM usuarios")
            ).scalar_one()
        self.assertEqual(count, 0)

    def test_login_succeeds_and_bad_credentials_are_rejected(self) -> None:
        self.assertEqual(self.register().status_code, 201)

        response = self.login()
        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        claims = jwt.decode(
            body["token"], self.jwt_secret, algorithms=["HS256"]
        )
        self.assertEqual(str(claims["id"]), str(body["user"]["id"]))
        self.assertEqual(body["user"]["rol"], "ADOPTANTE")
        self.assertNotIn("password_hash", response.text)

        wrong_password = self.login(password="incorrect password")
        self.assertEqual(wrong_password.status_code, 401)
        wrong_email = self.login(email="missing@example.com")
        self.assertEqual(wrong_email.status_code, 401)

    def test_me_accepts_valid_token_and_rejects_absent_invalid_and_expired_tokens(
        self,
    ) -> None:
        self.assertEqual(self.register().status_code, 201)
        token = self.login().json()["data"]["token"]

        valid = self.client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["data"]["user"]["email"], "ada@example.com")

        absent = self.client.get("/api/auth/me")
        self.assertEqual(absent.status_code, 401)
        invalid = self.client.get(
            "/api/auth/me", headers={"Authorization": "Bearer not-a-token"}
        )
        self.assertEqual(invalid.status_code, 401)

        expired_token = jwt.encode(
            {
                "sub": "1",
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            self.jwt_secret,
            algorithm="HS256",
        )
        expired = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        self.assertEqual(expired.status_code, 401)
        self.assertEqual(expired.json()["message"], "Token expired")


if __name__ == "__main__":
    unittest.main()

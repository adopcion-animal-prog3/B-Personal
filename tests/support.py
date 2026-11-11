import unittest
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.routes.auth import get_current_user
from app.services.historial import HistorialService
from app.services.solicitudes import SolicitudService


class AdoptionApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self._create_schema()
        self.app = create_app()
        self.app.state.solicitud_service = SolicitudService(self.engine)
        self.app.state.historial_service = HistorialService(self.engine)
        self.user: dict[str, Any] | None = {"id": 2, "rol": "ADOPTANTE"}
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def set_user(self, user_id: int = 2, role: str = "ADOPTANTE") -> None:
        self.user = {"id": user_id, "rol": role}

    def _create_schema(self) -> None:
        statements = (
            "CREATE TABLE usuarios ("
            "id INTEGER PRIMARY KEY, nombre VARCHAR(150) NOT NULL, "
            "email VARCHAR(255) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, "
            "rol VARCHAR(20) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE mascotas ("
            "id INTEGER PRIMARY KEY, nombre VARCHAR(150) NOT NULL, "
            "especie VARCHAR(100) NOT NULL, raza VARCHAR(120), edad INTEGER, "
            "sexo VARCHAR(20), descripcion TEXT, adoptada BOOLEAN NOT NULL DEFAULT 0, "
            "creado_por INTEGER REFERENCES usuarios(id), "
            "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE solicitudes_adopcion ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE, "
            "mascota_id INTEGER NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE, "
            "estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE', mensaje TEXT, "
            "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP)",
            "CREATE TABLE historial_clinico ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "mascota_id INTEGER NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE, "
            "fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "descripcion TEXT NOT NULL, veterinario VARCHAR(200), "
            "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP)",
        )
        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
            connection.execute(
                text(
                    "INSERT INTO usuarios (id, nombre, email, password_hash, rol) "
                    "VALUES (1, 'Admin', 'admin@example.com', 'hash', 'ADMIN'), "
                    "(2, 'Adoptante', 'adoptante@example.com', 'hash', 'ADOPTANTE'), "
                    "(3, 'Otro', 'otro@example.com', 'hash', 'ADOPTANTE')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO mascotas (id, nombre, especie, adoptada) "
                    "VALUES (1, 'Luna', 'Perro', FALSE), (2, 'Nina', 'Gato', TRUE)"
                )
            )

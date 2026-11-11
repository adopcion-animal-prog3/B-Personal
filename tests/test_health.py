import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.health import HealthService


class FakeDatabaseRepository:
    def __init__(self, available: bool) -> None:
        self._available = available

    def check_connection(self) -> bool:
        return self._available


class HealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()

    def test_api_health_is_available_without_database(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_database_health_reports_available_and_unavailable_states(self) -> None:
        self.app.state.health_service = HealthService(
            FakeDatabaseRepository(available=True)
        )
        available = self.client.get("/health/db")
        self.assertEqual(available.status_code, 200)
        self.assertEqual(available.json(), {"status": "ok"})

        self.app.state.health_service = HealthService(
            FakeDatabaseRepository(available=False)
        )
        unavailable = self.client.get("/health/db")
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(unavailable.json()["message"], "Database unavailable")
        self.assertEqual(unavailable.json()["status"], "error")


if __name__ == "__main__":
    unittest.main()

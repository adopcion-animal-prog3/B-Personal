import unittest

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import create_app
from app.routes.auth import get_current_user
from app.services.mascotas import MascotaService


class MissingMascotaRepository:
    def get(self, _: int) -> None:
        return None


class HttpErrorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        self.client.close()

    def assert_error_envelope(self, response, status_code: int) -> dict:
        self.assertEqual(response.status_code, status_code)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["message"], body["error"]["message"])
        return body

    def test_validation_errors_use_400_and_safe_field_details(self) -> None:
        body = self.assert_error_envelope(
            self.client.post("/api/auth/register", json={"password": "do-not-echo"}),
            400,
        )

        self.assertEqual(body["message"], "Invalid request data")
        self.assertTrue(body["errors"])
        self.assertNotIn("do-not-echo", str(body))
        self.assertNotIn("input", str(body))

    def test_authentication_and_permission_errors_keep_common_envelope(self) -> None:
        response = self.client.get("/api/auth/me")
        unauthenticated = self.assert_error_envelope(response, 401)
        self.assertEqual(unauthenticated["message"], "Authentication required")
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

        self.app.dependency_overrides[get_current_user] = lambda: {
            "id": 7,
            "rol": "ADOPTANTE",
        }
        forbidden = self.assert_error_envelope(
            self.client.get("/api/mascotas/1/historial"), 403
        )
        self.assertEqual(forbidden["message"], "Insufficient permissions")

    def test_missing_resource_and_unavailable_database_are_distinct(self) -> None:
        self.app.state.mascota_service = MascotaService.__new__(MascotaService)
        self.app.state.mascota_service._repository = MissingMascotaRepository()
        not_found = self.assert_error_envelope(
            self.client.get("/api/mascotas/987"), 404
        )
        self.assertIn("not found", not_found["message"])

        self.app.state.mascota_service = MascotaService(None)
        unavailable = self.assert_error_envelope(
            self.client.get("/api/mascotas"), 503
        )
        self.assertEqual(unavailable["message"], "Database unavailable")
        self.assertNotIn("DATABASE_URL", str(unavailable))

    def test_unexpected_errors_return_generic_message_without_exception_details(
        self,
    ) -> None:
        internal_detail = "private-database-detail"

        def fail_with_internal_detail() -> None:
            raise RuntimeError(internal_detail)

        self.app.add_api_route(
            "/test-unexpected-error",
            fail_with_internal_detail,
            methods=["GET"],
        )
        with self.assertLogs("app.errors", level="ERROR") as captured:
            response = self.client.get("/test-unexpected-error")
        body = self.assert_error_envelope(response, 500)

        self.assertEqual(body["message"], "Internal server error")
        self.assertNotIn(internal_detail, response.text)
        self.assertIn("route=/test-unexpected-error", captured.output[0])
        self.assertNotIn(internal_detail, captured.output[0])

    def test_database_errors_use_service_unavailable_without_sql_details(self) -> None:
        internal_detail = "postgres password=do-not-log"

        def fail_with_database_detail() -> None:
            raise SQLAlchemyError(internal_detail)

        self.app.add_api_route(
            "/test-database-error",
            fail_with_database_detail,
            methods=["GET"],
        )
        with self.assertLogs("app.errors", level="ERROR") as captured:
            response = self.client.get("/test-database-error")
        body = self.assert_error_envelope(response, 503)

        self.assertEqual(body["message"], "Database operation failed")
        self.assertNotIn(internal_detail, response.text)
        self.assertNotIn(internal_detail, captured.output[0])

    def test_openapi_documents_error_contract_without_default_422(self) -> None:
        schema = self.client.get("/openapi.json").json()
        operation = schema["paths"]["/api/auth/register"]["post"]

        for code in ("400", "401", "403", "404", "409", "500", "503"):
            self.assertIn(code, operation["responses"])
        self.assertNotIn("422", operation["responses"])
        error_schema = operation["responses"]["400"]["content"][
            "application/json"
        ]["schema"]
        self.assertEqual(
            error_schema["$ref"], "#/components/schemas/ErrorResponse"
        )
        self.assertIn("RegisterRequest", schema["components"]["schemas"])


if __name__ == "__main__":
    unittest.main()

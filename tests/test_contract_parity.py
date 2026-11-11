import unittest

from fastapi.testclient import TestClient

from app.main import create_app


class EndpointContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        self.client.close()

    def test_all_expected_endpoint_methods_are_documented(self) -> None:
        schema = self.client.get("/openapi.json").json()
        paths = schema["paths"]
        expected = {
            "/health": {"get"},
            "/health/db": {"get"},
            "/api/auth/register": {"post"},
            "/api/auth/login": {"post"},
            "/api/auth/me": {"get"},
            "/api/mascotas": {"get", "post"},
            "/api/mascotas/{mascota_id}": {"get", "put", "delete"},
            "/api/solicitudes": {"get", "post"},
            "/api/solicitudes/{solicitud_id}": {"get", "put"},
            "/api/mascotas/{mascota_id}/historial": {"get", "post"},
            "/api/historial/{historial_id}": {"put", "delete"},
        }

        self.assertEqual(set(paths), set(expected))
        for path, methods in expected.items():
            with self.subTest(path=path):
                self.assertEqual(
                    {
                        method
                        for method in paths[path]
                        if method in {"get", "post", "put", "delete", "patch"}
                    },
                    methods,
                )

    def test_public_auth_schemas_never_expose_password_or_hash(self) -> None:
        schemas = self.client.get("/openapi.json").json()["components"]["schemas"]
        public_user = schemas["PublicUser"]["properties"]
        auth_response = schemas["AuthTokenResponse"]["properties"]

        self.assertNotIn("password", public_user)
        self.assertNotIn("password_hash", public_user)
        self.assertNotIn("password_hash", auth_response)


if __name__ == "__main__":
    unittest.main()

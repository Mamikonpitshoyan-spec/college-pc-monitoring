"""Admin password: first-run setup, login, page and API protection."""

import unittest

from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import engine
from app.main import create_app


class AdminAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(create_app())
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def setUp(self) -> None:
        from app.monitoring.engine import engine as health_engine
        from app.services.pairing import pairing_service

        health_engine.reset()
        pairing_service.reset()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def test_first_run_redirects_to_setup(self) -> None:
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["location"].startswith("/setup"))

    def test_setup_creates_password_and_session(self) -> None:
        response = self.client.post(
            "/setup", data={"password": "secret1", "confirm": "secret1"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["location"].startswith("/"))
        self.assertIn("admin_session", response.cookies)

    def test_setup_requires_matching_passwords(self) -> None:
        response = self.client.post(
            "/setup", data={"password": "secret1", "confirm": "other1"},
            follow_redirects=False,
        )
        self.assertTrue(response.headers["location"].startswith("/setup?error"))

    def test_after_setup_dashboard_requires_login(self) -> None:
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})
        self.client.cookies.clear()
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["location"].startswith("/login"))

    def test_login_with_wrong_password_stays_on_login(self) -> None:
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})
        self.client.cookies.clear()
        response = self.client.post(
            "/login", data={"password": "wrong"}, follow_redirects=False
        )
        self.assertTrue(response.headers["location"].startswith("/login?error"))

    def test_login_with_correct_password_grants_access(self) -> None:
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})
        self.client.cookies.clear()
        self.client.post("/login", data={"password": "secret1"})
        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("Дашборд", dashboard.text)

    def test_admin_api_protected_but_agent_api_public(self) -> None:
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})
        self.client.cookies.clear()
        # админ-API закрыт
        self.assertEqual(self.client.get("/api/devices").status_code, 401)
        self.assertEqual(self.client.get("/api/monitoring/events").status_code, 401)
        # агент-API открыт (его защита — собственные токены)
        register = self.client.post(
            "/api/agent/register",
            json={
                "agent_id": "agent-auth-001",
                "hostname": "auth-host",
                "agent_version": "0.4.0",
                "schema_version": "1.0",
            },
            headers={"X-Registration-Key": "test-registration-key"},
        )
        self.assertEqual(register.status_code, 201)

    def test_logout_clears_session(self) -> None:
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})
        self.client.get("/logout", follow_redirects=False)
        self.assertEqual(self.client.get("/", follow_redirects=False).status_code, 302)


if __name__ == "__main__":
    unittest.main()

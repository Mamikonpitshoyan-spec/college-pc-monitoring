"""Pairing tests: one-time codes, approval, rejection, expiry."""

import unittest

from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import engine
from app.main import create_app
from app.services.pairing import PENDING_APPROVAL, pairing_service


class PairingTests(unittest.TestCase):
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

        health_engine.reset()
        pairing_service.reset()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})

    def _create_code(self) -> str:
        response = self.client.post("/api/monitoring/pairing")
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["code"]

    def _attach(self, code: str, agent_id: str = "agent-pair-001") -> dict:
        response = self.client.post(
            "/api/agent/pair",
            json={
                "pairing_code": code,
                "agent_id": agent_id,
                "hostname": "pair-host",
                "ip_address": "192.168.1.90",
                "os_name": "Windows",
                "os_version": "10.0",
                "agent_version": "0.4.0",
                "schema_version": "1.0",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_code_format_and_expiry_field(self) -> None:
        import re

        code = self._create_code()
        self.assertIsNotNone(re.match(r"^[A-Z0-9]{3}-[A-Z0-9]{3}$", code))

    def test_full_approve_flow_issues_working_token(self) -> None:
        code = self._create_code()
        state = self._attach(code)
        self.assertEqual(state["status"], PENDING_APPROVAL)

        # устройство появилось в списке со статусом ожидания
        devices = self.client.get("/api/devices").json()
        self.assertEqual(devices[0]["connection_status"], PENDING_APPROVAL)

        # админ одобряет
        approved = self.client.post(f"/api/monitoring/pairing/{code}/approve")
        self.assertEqual(approved.status_code, 200, approved.text)

        # агент получает токен на следующем опросе
        state = self.client.get(f"/api/agent/pair/{code}/status").json()
        self.assertEqual(state["status"], "APPROVED")
        token = state["api_token"]
        self.assertIsInstance(token, str)

        # токен работает
        heartbeat = self.client.post(
            "/api/agent/heartbeat",
            json={"agent_id": "agent-pair-001"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(heartbeat.status_code, 200, heartbeat.text)

    def test_code_is_single_use(self) -> None:
        code = self._create_code()
        self._attach(code, agent_id="agent-pair-001")
        self.client.post(f"/api/monitoring/pairing/{code}/approve")
        # второй агент по тому же коду — конфликт
        second = self.client.post(
            "/api/agent/pair",
            json={
                "pairing_code": code,
                "agent_id": "agent-pair-002",
                "hostname": "other-host",
                "agent_version": "0.4.0",
                "schema_version": "1.0",
            },
        )
        self.assertEqual(second.status_code, 409, second.text)

    def test_reject_removes_device(self) -> None:
        code = self._create_code()
        self._attach(code)
        rejected = self.client.post(f"/api/monitoring/pairing/{code}/reject")
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(self.client.get("/api/devices").json(), [])
        state = self.client.get(f"/api/agent/pair/{code}/status").json()
        self.assertEqual(state["status"], "REJECTED")

    def test_unknown_code_attach_returns_404(self) -> None:
        response = self.client.post(
            "/api/agent/pair",
            json={
                "pairing_code": "XXX-XXX",
                "agent_id": "agent-pair-003",
                "hostname": "host",
                "agent_version": "0.4.0",
                "schema_version": "1.0",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_expired_code_attach_returns_404(self) -> None:
        from datetime import timedelta

        from app.services.agent_service import utc_now

        code = self._create_code()
        record = pairing_service._codes[code]
        object.__setattr__(
            record, "expires_at", utc_now() - timedelta(seconds=1)
        )
        response = self.client.post(
            "/api/agent/pair",
            json={
                "pairing_code": code,
                "agent_id": "agent-pair-004",
                "hostname": "host",
                "agent_version": "0.4.0",
                "schema_version": "1.0",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_approve_without_device_returns_400(self) -> None:
        code = self._create_code()
        response = self.client.post(f"/api/monitoring/pairing/{code}/approve")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

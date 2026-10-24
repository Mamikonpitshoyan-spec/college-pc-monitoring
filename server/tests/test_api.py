"""Integration tests for the Stage 3 Monitoring Server REST API."""

import os
import unittest

# These must be set before importing app settings/session modules.
os.environ["DATABASE_URL"] = "sqlite:///./test_monitoring.db"
os.environ["AGENT_REGISTRATION_KEY"] = "test-registration-key"
os.environ["AGENT_TOKEN_PEPPER"] = "test-token-pepper-not-for-production"

from fastapi.testclient import TestClient
from sqlalchemy import inspect

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import engine
from app.main import create_app


class MonitoringApiTests(unittest.TestCase):
    """Run API operations against the configured SQLite test database."""

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
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})

    @staticmethod
    def registration_payload() -> dict[str, str]:
        return {
            "agent_id": "agent-test-001",
            "hostname": "test-workstation",
            "ip_address": "192.168.1.25",
            "os_name": "Windows",
            "os_version": "10.0.26200",
            "agent_version": "0.2.0",
            "schema_version": "1.0",
        }

    def register_agent(self) -> tuple[dict[str, object], str]:
        response = self.client.post(
            "/api/agent/register",
            json=self.registration_payload(),
            headers={"X-Registration-Key": "test-registration-key"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        token = body["api_token"]
        self.assertIsInstance(token, str)
        return body, token

    @staticmethod
    def stage_two_metrics_payload() -> dict[str, object]:
        """A representative unchanged Stage 2 envelope with nullable hardware."""
        return {
            "agent_id": "agent-test-001",
            "schema_version": "1.0",
            "collected_at": "2026-10-01T15:50:23.268964+00:00",
            "cpu": {"model": "Example CPU", "usage_percent": 12.5, "frequency_MHz": None},
            "ram": {"total_bytes": 16_000_000_000, "usage_percent": 50.0},
            "disk": {"partitions": [], "io": {"read_speed_Bps": 0.0, "write_speed_Bps": 128.0}},
            "network": {"interfaces": []},
            "disk_io": {"read_speed_Bps": 0.0},
            "network_interface_with_traffic": None,
            "gpu": {"adapters": None},
            "temperature": {"unit": "celsius", "sensors": None},
            "system": {"hostname": "test-workstation", "uptime_seconds": 120.0},
            "bios": {"serial_number": None},
            "future_stage_field": {"preserved": True},
        }

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "stage": "9"})

    def test_database_schema_is_created(self) -> None:
        table_names = set(inspect(engine).get_table_names())
        self.assertTrue({"devices", "metrics", "alerts", "events", "settings"}.issubset(table_names))

    def test_agent_registration(self) -> None:
        body, _ = self.register_agent()
        self.assertTrue(body["registered"])
        self.assertEqual(body["agent_id"], "agent-test-001")

    def test_duplicate_registration_does_not_create_device_or_issue_new_token(self) -> None:
        first, _ = self.register_agent()
        response = self.client.post(
            "/api/agent/register",
            json=self.registration_payload(),
            headers={"X-Registration-Key": "test-registration-key"},
        )
        self.assertEqual(response.status_code, 201)
        duplicate = response.json()
        self.assertFalse(duplicate["registered"])
        self.assertIsNone(duplicate["api_token"])
        self.assertEqual(duplicate["device_id"], first["device_id"])
        self.assertEqual(len(self.client.get("/api/devices").json()), 1)

    def test_heartbeat_updates_registered_device(self) -> None:
        _, token = self.register_agent()
        response = self.client.post(
            "/api/agent/heartbeat",
            json={"agent_id": "agent-test-001"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["connection_status"], "ONLINE")

    def test_metrics_submission_and_retrieval_preserves_payload(self) -> None:
        registration, token = self.register_agent()
        payload = self.stage_two_metrics_payload()
        response = self.client.post(
            "/api/agent/metrics",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["schema_version"], "1.0")

        device_id = registration["device_id"]
        device_response = self.client.get(f"/api/devices/{device_id}")
        self.assertEqual(device_response.status_code, 200)
        self.assertEqual(device_response.json()["agent_id"], "agent-test-001")

        metrics_response = self.client.get(f"/api/devices/{device_id}/metrics")
        self.assertEqual(metrics_response.status_code, 200)
        stored = metrics_response.json()[0]["payload"]
        self.assertEqual(stored["gpu"], {"adapters": None})
        self.assertEqual(stored["temperature"], {"unit": "celsius", "sensors": None})
        self.assertEqual(stored["future_stage_field"], {"preserved": True})

    def test_unknown_device_metrics_returns_404(self) -> None:
        response = self.client.get("/api/devices/999999/metrics")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Device not found.")

    def test_openapi_includes_device_metrics_route(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/devices/{device_id}/metrics", response.json()["paths"])

    def test_invalid_token_is_rejected(self) -> None:
        self.register_agent()
        response = self.client.post(
            "/api/agent/heartbeat",
            json={"agent_id": "agent-test-001"},
            headers={"Authorization": "Bearer invalid-token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_schema_is_rejected(self) -> None:
        _, token = self.register_agent()
        payload = self.stage_two_metrics_payload()
        payload["schema_version"] = "2.0"
        response = self.client.post(
            "/api/agent/metrics",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 422)

    def test_invalid_payload_and_malformed_json_are_rejected(self) -> None:
        _, token = self.register_agent()
        invalid_payload = self.stage_two_metrics_payload()
        invalid_payload["cpu"] = ["not-an-object"]
        invalid_response = self.client.post(
            "/api/agent/metrics",
            json=invalid_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(invalid_response.status_code, 422)

        malformed_response = self.client.post(
            "/api/agent/metrics",
            content=b'{"agent_id":',
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        self.assertEqual(malformed_response.status_code, 422)


class DashboardApiTests(unittest.TestCase):
    """Level 6 additions: latest summary, metrics limit, and HTML pages."""

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
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})

    def _register(self) -> str:
        """Register the test agent on a fresh database and return its token."""
        body = self.client.post(
            "/api/agent/register",
            json={
                "agent_id": "agent-dash-001",
                "hostname": "dash-host",
                "ip_address": "192.168.1.77",
                "os_name": "Windows",
                "os_version": "10.0",
                "agent_version": "0.4.0",
                "schema_version": "1.0",
            },
            headers={"X-Registration-Key": "test-registration-key"},
        ).json()
        return body["api_token"]

    def _submit_metric(self, token: str, cpu: float) -> None:
        response = self.client.post(
            "/api/agent/metrics",
            json={
                "agent_id": "agent-dash-001",
                "schema_version": "1.0",
                "collected_at": "2026-10-04T10:00:00+00:00",
                "cpu": {"usage_percent": cpu},
                "ram": {"usage_percent": 40.0},
                "disk": {"partitions": [{"mountpoint": "C:\\", "usage_percent": 61.5}]},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_devices_list_includes_latest_summary(self) -> None:
        token = self._register()
        self._submit_metric(token, 12.5)
        devices = self.client.get("/api/devices").json()
        self.assertEqual(len(devices), 1)
        latest = devices[0]["latest"]
        self.assertIsNotNone(latest)
        self.assertEqual(latest["cpu_percent"], 12.5)
        self.assertEqual(latest["ram_percent"], 40.0)
        self.assertEqual(latest["disk_percent"], 61.5)

    def test_metrics_limit_returns_newest_first_subset(self) -> None:
        token = self._register()
        self._submit_metric(token, 10.0)
        self._submit_metric(token, 20.0)
        self._submit_metric(token, 30.0)
        metrics = self.client.get("/api/devices/1/metrics?limit=2").json()
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0]["payload"]["cpu"]["usage_percent"], 30.0)
        self.assertEqual(metrics[1]["payload"]["cpu"]["usage_percent"], 20.0)

    def test_dashboard_and_device_pages_render(self) -> None:
        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("Дашборд", dashboard.text)
        device_page = self.client.get("/devices/1")
        self.assertEqual(device_page.status_code, 200)
        self.assertIn("Устройство", device_page.text)


class HealthAlertsTests(unittest.TestCase):
    """Level 9 end-to-end: thresholds, anti-flapping, alerts, events."""

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
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})
        self.token = self.client.post(
            "/api/agent/register",
            json={
                "agent_id": "agent-health-001",
                "hostname": "health-host",
                "agent_version": "0.4.0",
                "schema_version": "1.0",
            },
            headers={"X-Registration-Key": "test-registration-key"},
        ).json()["api_token"]

    def _submit(self, cpu: float) -> None:
        response = self.client.post(
            "/api/agent/metrics",
            json={
                "agent_id": "agent-health-001",
                "schema_version": "1.0",
                "collected_at": "2026-10-04T12:00:00+00:00",
                "cpu": {"usage_percent": cpu},
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 201, response.text)

    def _health(self) -> str:
        return self.client.get("/api/devices/1").json()["health_status"]

    def test_health_commits_after_three_warning_samples(self) -> None:
        self._submit(20.0)
        self._submit(87.0)
        self.assertEqual(self._health(), "UNKNOWN")
        self._submit(87.0)
        self.assertEqual(self._health(), "UNKNOWN")
        self._submit(87.0)
        self.assertEqual(self._health(), "WARNING")

    def test_critical_health_and_alert_created(self) -> None:
        for _ in range(3):
            self._submit(97.0)
        self.assertEqual(self._health(), "CRITICAL")
        alerts = self.client.get("/api/monitoring/alerts").json()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], "CRITICAL")
        self.assertEqual(alerts[0]["status"], "OPEN")
        self.assertIn("CPU", alerts[0]["message"])

    def test_recovery_resolves_alert(self) -> None:
        for cpu in [97.0, 97.0, 97.0, 30.0, 30.0, 30.0]:
            self._submit(cpu)
        self.assertEqual(self._health(), "NORMAL")
        alerts = self.client.get("/api/monitoring/alerts").json()
        self.assertEqual(alerts[0]["status"], "RESOLVED")
        self.assertIsNotNone(alerts[0]["resolved_at"])

    def test_events_log_records_transitions(self) -> None:
        for cpu in [97.0, 97.0, 97.0, 30.0, 30.0, 30.0]:
            self._submit(cpu)
        events = self.client.get("/api/monitoring/events").json()
        event_types = [event["event_type"] for event in events]
        self.assertIn("METRIC_STATUS_CHANGED", event_types)
        self.assertIn("HEALTH_CHANGED", event_types)
        metric_events = [e for e in events if e["event_type"] == "METRIC_STATUS_CHANGED"]
        self.assertEqual(len(metric_events), 2)  # вход в CRITICAL и возврат в NORMAL


class PagesTests(unittest.TestCase):
    """All Level 6/9 dashboard pages render with their titles."""

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
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})

    def test_all_pages_render(self) -> None:
        cases = {
            "/": "Дашборд",
            "/devices": "Устройства",
            "/alerts": "Алерты",
            "/events": "Журнал событий",
            "/analytics": "История показателей",
            "/settings": "Настройки",
            "/devices/1": "Устройство",
        }
        for url, expected in cases.items():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertIn(expected, response.text, url)


class RetentionAndDeleteTests(unittest.TestCase):
    """Level 5 retention pruning and device deletion."""

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
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client.post("/setup", data={"password": "secret1", "confirm": "secret1"})
        self.token = self.client.post(
            "/api/agent/register",
            json={
                "agent_id": "agent-retention-001",
                "hostname": "retention-host",
                "agent_version": "0.4.0",
                "schema_version": "1.0",
            },
            headers={"X-Registration-Key": "test-registration-key"},
        ).json()["api_token"]

    def _submit(self, collected_at: str) -> None:
        response = self.client.post(
            "/api/agent/metrics",
            json={
                "agent_id": "agent-retention-001",
                "schema_version": "1.0",
                "collected_at": collected_at,
                "cpu": {"usage_percent": 10.0},
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_prune_removes_only_old_snapshots(self) -> None:
        from datetime import datetime, timedelta, timezone

        from app.database.session import SessionLocal
        from app.models.metric import Metric
        from app.monitoring.retention import prune_old_metrics
        from sqlalchemy import func, select

        now = datetime.now(timezone.utc)
        stale = (now - timedelta(days=30)).isoformat()
        fresh = (now - timedelta(minutes=5)).isoformat()
        self._submit(stale)   # старый
        self._submit(fresh)   # свежий
        database = SessionLocal()
        try:
            removed = prune_old_metrics(database, 48)
            remaining = database.scalar(select(func.count(Metric.id)))
        finally:
            database.close()
        self.assertEqual(removed, 1)
        self.assertEqual(remaining, 1)

    def test_delete_device_removes_it_from_list(self) -> None:
        devices = self.client.get("/api/devices").json()
        self.assertEqual(len(devices), 1)
        response = self.client.delete("/api/devices/1")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get("/api/devices").json(), [])

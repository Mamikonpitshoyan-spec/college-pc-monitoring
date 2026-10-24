"""Unit tests for the Level 4 agent client and reporting loop."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import httpx

from network.client import AgentApiClient, TokenStore, default_agent_id
from network.service import AgentReporter

_REGISTRATION_KEY = "unit-test-registration-key"


class LoopExit(Exception):
    """Raised by a stub sleep to stop the reporter loop deterministically."""


def _snapshot_stub() -> SimpleNamespace:
    """A collector stand-in whose collect() returns one deterministic snapshot."""
    snapshot = {
        "schema_version": "1.0",
        "collected_at": "2026-10-03T20:00:00+00:00",
        "cpu": {"usage_percent": 10.0},
    }
    return SimpleNamespace(collect=lambda: SimpleNamespace(to_dict=lambda: snapshot.copy()))


class RecordingHandler:
    """Collect requests and answer with a minimal valid server behavior."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.fail_metrics_times = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/api/agent/register":
            if request.headers.get("X-Registration-Key") != _REGISTRATION_KEY:
                return httpx.Response(401)
            return httpx.Response(201, json={"api_token": "issued-token", "registered": True})
        if request.headers.get("Authorization") != "Bearer issued-token":
            return httpx.Response(401)
        if request.url.path == "/api/agent/heartbeat":
            return httpx.Response(200, json={"connection_status": "ONLINE"})
        if request.url.path == "/api/agent/metrics":
            sent = len([r for r in self.requests if r.url.path == "/api/agent/metrics"])
            if sent <= self.fail_metrics_times:
                raise httpx.ConnectError("simulated outage", request=request)
            return httpx.Response(201, json={"metric_id": 42})
        return httpx.Response(404)


class AgentClientTests(unittest.TestCase):
    """Registration, token persistence, and authenticated reporting."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.token_path = Path(self._tmp.name) / "token.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def make_client(self, handler: RecordingHandler) -> AgentApiClient:
        return AgentApiClient(
            server_url="http://server.test:8000",
            registration_key=_REGISTRATION_KEY,
            token_store=TokenStore(self.token_path),
            transport=httpx.MockTransport(handler),
        )

    def test_default_agent_id_matches_server_pattern(self) -> None:
        import re

        agent_id = default_agent_id()
        self.assertGreaterEqual(len(agent_id), 3)
        self.assertIsNotNone(re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$", agent_id))

    def test_register_issues_and_persists_token(self) -> None:
        handler = RecordingHandler()
        client = self.make_client(handler)
        token = client.register("unit-agent-01")
        self.assertEqual(token, "issued-token")
        self.assertEqual(json.loads(self.token_path.read_text())["api_token"], token)

    def test_register_with_stored_token_skips_http(self) -> None:
        self.token_path.write_text(json.dumps({"agent_id": "a", "api_token": "saved"}))
        handler = RecordingHandler()
        client = self.make_client(handler)
        self.assertEqual(client.register("unit-agent-01"), "saved")
        register_calls = [r for r in handler.requests if r.url.path == "/api/agent/register"]
        self.assertEqual(register_calls, [])

    def test_heartbeat_and_metrics_use_bearer_token(self) -> None:
        handler = RecordingHandler()
        client = self.make_client(handler)
        client.register("unit-agent-01")
        client.heartbeat("unit-agent-01")
        snapshot = _snapshot_stub().collect().to_dict()
        metric_id = client.send_metrics("unit-agent-01", snapshot)
        self.assertEqual(metric_id, 42)
        metrics = [r for r in handler.requests if r.url.path == "/api/agent/metrics"][0]
        body = json.loads(metrics.content)
        self.assertEqual(body["agent_id"], "unit-agent-01")
        self.assertEqual(body["cpu"], {"usage_percent": 10.0})


class AgentReporterTests(unittest.TestCase):
    """Loop behavior: registration retry, reporting, and outage recovery."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.token_path = Path(self._tmp.name) / "token.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_single_cycle_reports_heartbeat_and_metrics(self) -> None:
        handler = RecordingHandler()
        client = AgentApiClient(
            server_url="http://server.test:8000",
            registration_key=_REGISTRATION_KEY,
            token_store=TokenStore(self.token_path),
            transport=httpx.MockTransport(handler),
        )
        reporter = AgentReporter(
            agent_id="unit-agent-01",
            client=client,
            collector=_snapshot_stub(),
            report_interval_seconds=10.0,
            sleep=lambda _: None,
        )
        reporter.run_forever(once=True)
        paths = [r.url.path for r in handler.requests]
        self.assertEqual(
            paths, ["/api/agent/register", "/api/agent/heartbeat", "/api/agent/metrics"]
        )

    def test_outage_is_tolerated_and_recovered(self) -> None:
        handler = RecordingHandler()
        handler.fail_metrics_times = 2
        waits: list[float] = []

        client = AgentApiClient(
            server_url="http://server.test:8000",
            registration_key=_REGISTRATION_KEY,
            token_store=TokenStore(self.token_path),
            transport=httpx.MockTransport(handler),
        )

        def sleep_and_stop(seconds: float) -> None:
            waits.append(seconds)
            if len(waits) >= 3:
                raise LoopExit

        reporter = AgentReporter(
            agent_id="unit-agent-01",
            client=client,
            collector=_snapshot_stub(),
            report_interval_seconds=10.0,
            sleep=sleep_and_stop,
        )
        reporter._sleep_step = 999.0  # один сон = вся задержка, шаги не важны
        with self.assertRaises(LoopExit):
            reporter.run_forever()
        metric_calls = [r for r in handler.requests if r.url.path == "/api/agent/metrics"]
        self.assertGreaterEqual(len(metric_calls), 3)
        self.assertEqual(waits[0], 2.0)
        self.assertEqual(waits[1], 4.0)


if __name__ == "__main__":
    unittest.main()


class AgentReporterStopTests(unittest.TestCase):
    """The service wrapper needs a loop that ends on a stop request."""

    def test_run_forever_exits_on_stop_check_after_first_cycle(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            handler = RecordingHandler()
            flag = {"stop": False}

            def stop_after_first_cycle() -> bool:
                return flag["stop"]

            base = _snapshot_stub()

            def collect_and_request_stop():
                flag["stop"] = True
                return base.collect()

            collector = SimpleNamespace(collect=collect_and_request_stop)
            client = AgentApiClient(
                server_url="http://server.test:8000",
                registration_key=_REGISTRATION_KEY,
                token_store=TokenStore(Path(tmp) / "token.json"),
                transport=httpx.MockTransport(handler),
            )
            reporter = AgentReporter(
                agent_id="unit-agent-01",
                client=client,
                collector=collector,
                report_interval_seconds=10.0,
                sleep=lambda _: None,
                stop_check=stop_after_first_cycle,
            )
            reporter.run_forever()  # must return after exactly one cycle
            paths = [r.url.path for r in handler.requests]
            self.assertEqual(
                paths, ["/api/agent/register", "/api/agent/heartbeat", "/api/agent/metrics"]
            )

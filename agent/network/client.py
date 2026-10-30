"""HTTP client for Monitoring Server registration, heartbeat, and metrics."""

from __future__ import annotations

import json
import logging
import platform
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

AGENT_VERSION = "0.4.0"
METRICS_SCHEMA_VERSION = "1.0"

_INVALID_AGENT_ID_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def default_agent_id() -> str:
    """Derive a server-valid agent id from the hostname."""
    hostname = socket.gethostname() or "unknown-host"
    sanitized = _INVALID_AGENT_ID_CHARS.sub("-", hostname).strip("-._")
    if not sanitized:
        sanitized = "unknown-host"
    if not re.match(r"^[A-Za-z0-9]", sanitized):
        sanitized = f"pc-{sanitized}"
    if len(sanitized) < 3:
        sanitized = f"{sanitized}-pc"
    return sanitized[:128]


def detect_lan_ip(server_url: str) -> str | None:
    """Return the local IP that routes to the server without sending packets."""
    try:
        parts = urlsplit(server_url)
        host = parts.hostname or "127.0.0.1"
        port = parts.port or (443 if parts.scheme == "https" else 80)
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect((host, port))
            return probe.getsockname()[0]
        finally:
            probe.close()
    except OSError:
        logger.warning("Unable to detect the local LAN IP address.", exc_info=True)
        return None


class TokenStore:
    """Persist the registration token outside source code."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> str | None:
        """Return the saved token, or None when missing or corrupted."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return None
        token = data.get("api_token")
        return token if isinstance(token, str) and token else None

    def save(self, agent_id: str, api_token: str) -> None:
        self._path.write_text(
            json.dumps({"agent_id": agent_id, "api_token": api_token}, indent=2),
            encoding="utf-8",
        )
        logger.info("Agent token saved to %s.", self._path)

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)


class AgentApiClient:
    """Speak the agent REST contract against one Monitoring Server."""

    def __init__(
        self,
        server_url: str,
        registration_key: str | None = None,
        request_timeout_seconds: float = 5.0,
        token_store: TokenStore | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=server_url.rstrip("/"),
            timeout=request_timeout_seconds,
            headers={"User-Agent": f"monitoring-agent/{AGENT_VERSION}"},
            transport=transport,
        )
        self._registration_key = registration_key
        self._token_store = token_store or TokenStore(".agent_token.json")
        self._token: str | None = None

    @property
    def token(self) -> str | None:
        return self._token

    @property
    def base_url(self) -> str:
        """The Monitoring Server URL this client talks to."""
        return str(self._client.base_url)

    def close(self) -> None:
        self._client.close()

    def load_stored_token(self) -> str | None:
        """Adopt the token saved by an earlier run (e.g. before a reboot)."""
        stored = self._token_store.load()
        if stored:
            self._token = stored
        return stored

    def reset_token(self) -> None:
        """Forget the stored token so the next cycle re-registers."""
        self._token = None
        self._token_store.clear()

    def register(self, agent_id: str) -> str:
        """Attach with a stored token or register once to receive a new one."""
        stored = self._token_store.load()
        if stored:
            self._token = stored
            logger.info("Reusing the stored registration token for '%s'.", agent_id)
            return stored

        response = self._client.post(
            "/api/agent/register",
            json={
                "agent_id": agent_id,
                "hostname": socket.gethostname() or agent_id,
                "ip_address": detect_lan_ip(str(self._client.base_url)),
                "os_name": platform.system() or None,
                "os_version": platform.version() or None,
                "agent_version": AGENT_VERSION,
                "schema_version": METRICS_SCHEMA_VERSION,
            },
            headers=self._registration_headers(),
        )
        response.raise_for_status()
        token = response.json().get("api_token")
        if not token:
            raise RuntimeError(
                "The server already knows this agent_id but no token file exists; "
                "restore .agent_token.json or delete the device on the server."
            )
        self._token = token
        self._token_store.save(agent_id, token)
        return token

    def heartbeat(self, agent_id: str) -> None:
        response = self._client.post(
            "/api/agent/heartbeat",
            json={"agent_id": agent_id},
            headers=self._auth_headers(),
        )
        response.raise_for_status()

    def attach_pairing(self, pairing_code: str, agent_id: str) -> str:
        """Submit identity with a pairing code; returns the request state."""
        response = self._client.post(
            "/api/agent/pair",
            json={
                "pairing_code": pairing_code,
                "agent_id": agent_id,
                "hostname": socket.gethostname() or agent_id,
                "ip_address": detect_lan_ip(str(self._client.base_url)),
                "os_name": platform.system() or None,
                "os_version": platform.version() or None,
                "agent_version": AGENT_VERSION,
                "schema_version": METRICS_SCHEMA_VERSION,
            },
        )
        response.raise_for_status()
        return response.json()["status"]

    def pairing_status(self, pairing_code: str) -> dict:
        """Poll the decision: {status: PENDING_APPROVAL|APPROVED|REJECTED|EXPIRED, api_token?}."""
        response = self._client.get(f"/api/agent/pair/{pairing_code}/status")
        response.raise_for_status()
        return response.json()

    def apply_token(self, agent_id: str, token: str) -> None:
        """Store a token received through pairing (same as registration)."""
        self._token = token
        self._token_store.save(agent_id, token)

    def send_metrics(self, agent_id: str, snapshot: dict) -> int:
        """Submit one full metrics snapshot; returns the stored metric id."""
        response = self._client.post(
            "/api/agent/metrics",
            json={"agent_id": agent_id, **snapshot},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return int(response.json()["metric_id"])

    def _registration_headers(self) -> dict[str, str]:
        if not self._registration_key:
            raise RuntimeError("MONITORING_REGISTRATION_KEY is not configured.")
        return {"X-Registration-Key": self._registration_key}

    def _auth_headers(self) -> dict[str, str]:
        if not self._token:
            raise RuntimeError("Agent is not authenticated; register() must run first.")
        return {"Authorization": f"Bearer {self._token}"}

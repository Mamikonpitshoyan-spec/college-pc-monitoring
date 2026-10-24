"""Background reporting loop with automatic reconnection and backoff."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from network.client import AgentApiClient

logger = logging.getLogger(__name__)

RECONNECT_BASE_SECONDS = 2.0
RECONNECT_MAX_SECONDS = 60.0


class AgentReporter:
    """Register once, then report heartbeat and metrics on a fixed interval.

    Connection failures never crash the loop; they switch the agent into a
    reconnection backoff until the server becomes reachable again. An
    optional ``stop_check`` callback (used by the Windows Service wrapper)
    ends the loop gracefully between cycles.
    """

    def __init__(
        self,
        agent_id: str,
        client: AgentApiClient,
        collector: Any,
        report_interval_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
        stop_check: Callable[[], bool] | None = None,
        on_status: Callable[[dict], None] | None = None,
        pair_code: str | None = None,
        on_paired: Callable[[], None] | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._client = client
        self._collector = collector
        self._interval = report_interval_seconds
        self._sleep = sleep
        self._stop_check = stop_check
        self._sleep_step = 1.0
        self._on_status = on_status
        self._pair_code = pair_code
        self._on_paired = on_paired
        self._connected = False
        self._last_report_at: str | None = None
        self._last_error: str | None = None
        self._last_cycle_seconds: float | None = None
        self._last_snapshot: dict[str, Any] | None = None
        self._headline: dict[str, Any] = {}

    def _emit_status(self) -> None:
        """Publish the current connection state for the local status app."""
        if self._on_status is None:
            return
        try:
            self._on_status(
                {
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "connected": self._connected,
                    "agent_id": self._agent_id,
                    "server_url": str(self._client.base_url),
                    "last_report_at": self._last_report_at,
                    "last_error": self._last_error,
                    "report_interval_seconds": self._interval,
                    "last_cycle_seconds": self._last_cycle_seconds,
                    "snapshot": self._last_snapshot,
                    **self._headline,
                }
            )
        except Exception:
            logger.warning("Status callback failed.", exc_info=True)

    def run_forever(self, once: bool = False) -> None:
        """Report cycles until interrupted; ``once`` performs a single cycle."""
        self._register_with_retry()
        attempt = 0
        while not (self._stop_check and self._stop_check()):
            try:
                self._report_cycle()
                attempt = 0
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 401:
                    logger.warning(
                        "The server rejected the stored token; re-registration is required."
                    )
                    self._client.reset_token()
                    self._register_with_retry()
                else:
                    attempt += 1
                    self._last_error = f"HTTP {error.response.status_code}"
                    self._connected = False
                    self._log_connection_lost(error, attempt)
            except (httpx.HTTPError, OSError) as error:
                attempt += 1
                self._last_error = error.__class__.__name__
                self._connected = False
                self._log_connection_lost(error, attempt)
            self._emit_status()
            if once:
                return
            self._sleep_interruptible(self._wait_seconds(attempt))

    def _sleep_interruptible(self, seconds: float) -> None:
        """Sleep in short steps so a service stop request is noticed quickly."""
        remaining = seconds
        while remaining > 0 and not (self._stop_check and self._stop_check()):
            step = min(self._sleep_step, remaining)
            self._sleep(step)
            remaining -= step

    def _report_cycle(self) -> None:
        cycle_started = time.monotonic()
        snapshot = self._collector.collect().to_dict()
        self._client.heartbeat(self._agent_id)
        metric_id = self._client.send_metrics(self._agent_id, snapshot)
        self._last_snapshot = snapshot
        self._last_cycle_seconds = round(time.monotonic() - cycle_started, 1)
        self._connected = True
        self._last_error = None
        self._last_report_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        headline = snapshot.get("cpu") or {}
        ram = snapshot.get("ram") or {}
        disk = snapshot.get("disk") or {}
        partitions = disk.get("partitions") or []
        usage_values = [
            part.get("usage_percent")
            for part in partitions
            if isinstance(part, dict) and isinstance(part.get("usage_percent"), (int, float))
        ]
        self._headline = {
            "cpu_percent": headline.get("usage_percent"),
            "ram_percent": ram.get("usage_percent"),
            "disk_percent": max(usage_values) if usage_values else None,
        }
        logger.info("Reported metrics snapshot %s.", metric_id)

    def _register_with_retry(self) -> None:
        """Stored token first (after reboot), else pairing code, else classic registration."""
        if not self._client.token and self._client.load_stored_token():
            logger.info("Reusing the stored token for '%s'.", self._agent_id)
            self._emit_status()
            return
        if self._pair_code and not self._client.token:
            self._pair_with_retry()
            return
        attempt = 0
        while not (self._stop_check and self._stop_check()):
            try:
                self._client.register(self._agent_id)
                logger.info(
                    "Agent '%s' is registered with the monitoring server.", self._agent_id
                )
                self._emit_status()
                return
            except (httpx.HTTPError, OSError, RuntimeError) as error:
                attempt += 1
                delay = self._backoff_seconds(attempt)
                self._last_error = error.__class__.__name__
                self._connected = False
                self._emit_status()
                logger.warning(
                    "Registration failed (%s). Retrying in %.0f s.", error, delay
                )
                self._sleep_interruptible(delay)

    def _pair_with_retry(self) -> None:
        """Attach with a pairing code and wait until the administrator approves."""
        attempt = 0
        rejected = False
        while not (self._stop_check and self._stop_check()):
            try:
                self._client.attach_pairing(self._pair_code, self._agent_id)
                rejected = False
                logger.info(
                    "Pairing request sent (code %s); waiting for administrator approval.",
                    self._pair_code,
                )
                while not (self._stop_check and self._stop_check()):
                    state = self._client.pairing_status(self._pair_code)
                    token = state.get("api_token")
                    if state.get("status") == "APPROVED" and token:
                        self._client.apply_token(self._agent_id, token)
                        logger.info("Pairing approved by the administrator; token stored.")
                        self._pair_code = None
                        if self._on_paired is not None:
                            try:
                                self._on_paired()
                            except Exception:
                                logger.warning("Unable to remove the used pairing code.", exc_info=True)
                        self._emit_status()
                        return
                    if state.get("status") in ("REJECTED", "EXPIRED"):
                        logger.error(
                            "Pairing %s. Ask the administrator for a new code, update "
                            "MONITORING_PAIRING_CODE and restart the agent.",
                            "was rejected" if state["status"] == "REJECTED" else "expired",
                        )
                        rejected = True
                        break
                    self._sleep_interruptible(3.0)
            except (httpx.HTTPError, OSError) as error:
                self._last_error = error.__class__.__name__
                self._connected = False
                self._emit_status()
            attempt += 1
            delay = 30.0 if rejected else self._backoff_seconds(attempt)
            logger.warning("Pairing attempt %d failed. Retrying in %.0f s.", attempt, delay)
            self._sleep_interruptible(delay)

    def _wait_seconds(self, attempt: int) -> float:
        """Normal reporting interval, plus backoff while reconnecting."""
        if attempt == 0:
            return self._interval
        return self._backoff_seconds(attempt)

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        return min(RECONNECT_BASE_SECONDS * (2 ** (attempt - 1)), RECONNECT_MAX_SECONDS)

    def _log_connection_lost(self, error: Exception, attempt: int) -> None:
        logger.warning(
            "Connection to the monitoring server failed (%s). Reconnecting in %.0f s.",
            error.__class__.__name__,
            self._backoff_seconds(attempt),
        )

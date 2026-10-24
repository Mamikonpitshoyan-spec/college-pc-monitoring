"""Operating-system and computer identity metrics."""

from __future__ import annotations

import logging
import platform
import socket
from time import time
from typing import Any

import psutil

from hardware.windows import WindowsCimClient

logger = logging.getLogger(__name__)


class SystemCollector:
    """Collect host properties available from Windows and Python."""

    def __init__(self, cim_client: WindowsCimClient) -> None:
        self._cim_client = cim_client

    def collect(self) -> dict[str, Any]:
        computer_system = self._cim_client.query_one(
            "Win32_ComputerSystem", ("Manufacturer", "Model")
        )
        try:
            uptime_seconds: float | None = max(0.0, time() - psutil.boot_time())
        except OSError as error:
            logger.warning("System uptime is unavailable: %s", error)
            uptime_seconds = None

        return {
            "hostname": socket.gethostname() or None,
            "os": platform.system() or None,
            "windows_version": platform.version() or None,
            "architecture": platform.machine() or None,
            "uptime_seconds": uptime_seconds,
            "manufacturer": self._value(computer_system, "Manufacturer"),
            "model": self._value(computer_system, "Model"),
        }

    @staticmethod
    def _value(source: dict[str, Any] | None, key: str) -> Any | None:
        return source.get(key) if source else None

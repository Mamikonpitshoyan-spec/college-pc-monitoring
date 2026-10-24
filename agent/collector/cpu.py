"""CPU metrics collected from psutil and native Windows CIM data."""

from __future__ import annotations

import logging
from typing import Any

import psutil

from hardware.windows import WindowsCimClient

logger = logging.getLogger(__name__)


class CpuCollector:
    """Collect CPU identity and current utilisation without synthetic fallbacks."""

    def __init__(self, cim_client: WindowsCimClient) -> None:
        self._cim_client = cim_client

    def collect(self) -> dict[str, Any]:
        processor = self._cim_client.query_one(
            "Win32_Processor",
            ("Name", "Manufacturer", "NumberOfCores", "NumberOfLogicalProcessors"),
        )
        frequency_mhz: float | None = None
        try:
            frequency = psutil.cpu_freq()
            if frequency is not None and frequency.current is not None:
                frequency_mhz = float(frequency.current)
        except (OSError, AttributeError) as error:
            logger.warning("CPU frequency is unavailable: %s", error)

        try:
            usage_percent: float | None = float(psutil.cpu_percent(interval=0.1))
        except OSError as error:
            logger.warning("CPU usage is unavailable: %s", error)
            usage_percent = None

        return {
            "model": self._value(processor, "Name"),
            "manufacturer": self._value(processor, "Manufacturer"),
            "physical_cores": self._integer_or_none(
                self._value(processor, "NumberOfCores")
            )
            or psutil.cpu_count(logical=False),
            "logical_processors": self._integer_or_none(
                self._value(processor, "NumberOfLogicalProcessors")
            )
            or psutil.cpu_count(logical=True),
            "usage_percent": usage_percent,
            "frequency_MHz": frequency_mhz,
        }

    @staticmethod
    def _value(source: dict[str, Any] | None, key: str) -> Any | None:
        return source.get(key) if source else None

    @staticmethod
    def _integer_or_none(value: Any | None) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

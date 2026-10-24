"""Versioned, local metrics envelope assembled from independent collectors."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from collector.cpu import CpuCollector
from collector.disk import DiskCollector
from collector.memory import MemoryCollector
from collector.network import NetworkCollector, PortsCollector
from hardware.bios import BiosCollector
from hardware.gpu import GpuCollector
from hardware.system import SystemCollector
from hardware.windows import WindowsCimClient
from sensors.temperature import TemperatureCollector

logger = logging.getLogger(__name__)

METRICS_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class MetricsSnapshot:
    """Stable envelope that later stages can transport and persist unchanged."""

    schema_version: str
    collected_at: str
    cpu: dict[str, Any] | None
    ram: dict[str, Any] | None
    disk: dict[str, Any] | None
    network: dict[str, Any] | None
    gpu: dict[str, Any] | None
    temperature: dict[str, Any] | None
    system: dict[str, Any] | None
    bios: dict[str, Any] | None
    ports: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-compatible built-in data types."""
        return asdict(self)


class MetricsCollector:
    """Coordinate isolated collectors while preserving partial real measurements."""

    def __init__(self) -> None:
        cim_client = WindowsCimClient()
        self._cpu = CpuCollector(cim_client)
        self._memory = MemoryCollector()
        self._disk = DiskCollector()
        self._network = NetworkCollector()
        self._gpu = GpuCollector(cim_client)
        self._temperature = TemperatureCollector()
        self._system = SystemCollector(cim_client)
        self._bios = BiosCollector(cim_client)
        self._ports = PortsCollector()

    def collect(self) -> MetricsSnapshot:
        """Create one snapshot; a failing section becomes null, never invented data."""
        return MetricsSnapshot(
            schema_version=METRICS_SCHEMA_VERSION,
            collected_at=datetime.now(timezone.utc).isoformat(),
            cpu=self._collect_section("cpu", self._cpu.collect),
            ram=self._collect_section("ram", self._memory.collect),
            disk=self._collect_section("disk", self._disk.collect),
            network=self._collect_section("network", self._network.collect),
            gpu=self._collect_section("gpu", self._gpu.collect),
            temperature=self._collect_section("temperature", self._temperature.collect),
            system=self._collect_section("system", self._system.collect),
            bios=self._collect_section("bios", self._bios.collect),
            ports=self._collect_section("ports", self._ports.collect),
        )

    def establish_rate_baseline(self) -> None:
        """Read only cumulative I/O counters before a later full snapshot.

        Static Windows CIM queries are intentionally excluded so the local CLI does
        not perform costly hardware discovery twice merely to calculate rates.
        """
        self._collect_section("disk counter baseline", self._disk.collect)
        self._collect_section("network counter baseline", self._network.collect)

    @staticmethod
    def _collect_section(
        name: str, collect: Callable[[], dict[str, Any]]
    ) -> dict[str, Any] | None:
        try:
            return collect()
        except Exception:
            logger.exception("Unable to collect %s metrics", name)
            return None

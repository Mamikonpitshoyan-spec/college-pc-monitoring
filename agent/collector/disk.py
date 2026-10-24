"""Disk capacity and aggregate I/O throughput metrics."""

from __future__ import annotations

import logging
from typing import Any

import psutil

from collector.rates import ByteCounters, ByteRateTracker

logger = logging.getLogger(__name__)


class DiskCollector:
    """Collect mounted partition usage and real aggregate read/write rates."""

    def __init__(self) -> None:
        self._rate_tracker = ByteRateTracker()

    def collect(self) -> dict[str, Any]:
        partitions: list[dict[str, Any]] = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except OSError as error:
                logger.warning("Disk usage is unavailable for %s: %s", partition.mountpoint, error)
                continue
            partitions.append(
                {
                    "device": partition.device or None,
                    "mountpoint": partition.mountpoint or None,
                    "filesystem": partition.fstype or None,
                    "options": partition.opts or None,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "usage_percent": usage.percent,
                }
            )

        io_counters = psutil.disk_io_counters()
        if io_counters is None:
            return {"partitions": partitions, "io": None}

        counters = ByteCounters(
            inbound_bytes=int(io_counters.read_bytes),
            outbound_bytes=int(io_counters.write_bytes),
        )
        rates = self._rate_tracker.sample({"aggregate": counters})["aggregate"]
        return {
            "partitions": partitions,
            "io": {
                "read_bytes": counters.inbound_bytes,
                "write_bytes": counters.outbound_bytes,
                "read_speed_Bps": rates.inbound_Bps,
                "write_speed_Bps": rates.outbound_Bps,
            },
        }

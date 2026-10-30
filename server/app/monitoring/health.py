"""Health logic: thresholds, aggregation, and anti-flapping.

Pure computation with no I/O so it is unit-testable in isolation.

Thresholds follow the project plan: CPU/RAM 80 % WARNING, 95 % CRITICAL;
disk 85 % WARNING, 95 % CRITICAL. Temperature and network deliberately have
no universal thresholds (plan section 12) and are not evaluated here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

NORMAL = "NORMAL"
WARNING = "WARNING"
CRITICAL = "CRITICAL"
UNKNOWN = "UNKNOWN"

_SEVERITY_ORDER = {NORMAL: 0, WARNING: 1, CRITICAL: 2}

# How many consecutive samples a new status must hold before it commits.
CONFIRMATION_SAMPLES = 3

_DEFAULT_THRESHOLDS = {
    "cpu": {"warning": 80.0, "critical": 95.0},
    "ram": {"warning": 80.0, "critical": 95.0},
    "disk": {"warning": 85.0, "critical": 95.0},
}


def classify_percent(value: float | None, thresholds: dict[str, float]) -> str | None:
    """Map one percentage reading to a status, or None when unavailable."""
    if value is None or not isinstance(value, (int, float)):
        return None
    if value >= thresholds["critical"]:
        return CRITICAL
    if value >= thresholds["warning"]:
        return WARNING
    return NORMAL


def extract_metric_statuses(payload: dict[str, Any]) -> dict[str, str | None]:
    """Read cpu/ram/disk percentages from one raw snapshot payload."""
    cpu = payload.get("cpu") or {}
    ram = payload.get("ram") or {}
    disk = payload.get("disk") or {}
    partition_usages = [
        item.get("usage_percent")
        for item in disk.get("partitions") or []
        if isinstance(item, dict) and isinstance(item.get("usage_percent"), (int, float))
    ]
    return {
        "cpu": classify_percent(cpu.get("usage_percent"), _DEFAULT_THRESHOLDS["cpu"]),
        "ram": classify_percent(ram.get("usage_percent"), _DEFAULT_THRESHOLDS["ram"]),
        "disk": classify_percent(
            max(partition_usages) if partition_usages else None,
            _DEFAULT_THRESHOLDS["disk"],
        ),
    }


def aggregate_health(statuses: list[str | None]) -> str:
    """Worst committed status wins; no data at all stays UNKNOWN."""
    present = [status for status in statuses if status in _SEVERITY_ORDER]
    if not present:
        return UNKNOWN
    return max(present, key=lambda status: _SEVERITY_ORDER[status])


@dataclass
class _MetricState:
    committed: str | None = None
    candidate: str | None = None
    count: int = 0


@dataclass
class MetricChange:
    metric: str
    from_status: str | None
    to_status: str


@dataclass
class DeviceHealthState:
    metrics: dict[str, _MetricState] = field(default_factory=dict)

    def feed(self, metric: str, raw_status: str | None) -> MetricChange | None:
        """Advance the anti-flap state machine for one metric reading.

        A status change commits only after CONFIRMATION_SAMPLES consecutive
        equal readings, so a single spike like 79 / 81 / 79 never flips the
        committed value (plan section 14).
        """
        state = self.metrics.setdefault(metric, _MetricState())
        if raw_status is None:
            return None
        if state.candidate == raw_status:
            state.count += 1
        else:
            state.candidate = raw_status
            state.count = 1
        if state.count >= CONFIRMATION_SAMPLES and state.committed != raw_status:
            change = MetricChange(metric, state.committed, raw_status)
            state.committed = raw_status
            return change
        return None

    def committed_statuses(self) -> list[str | None]:
        return [
            state.committed
            for state in self.metrics.values()
            if state.committed is not None
        ]

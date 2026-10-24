"""Health engine: applies Level 9 logic to devices and persists alerts/events."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.device import Device
from app.models.event import Event
from app.monitoring.health import (
    CRITICAL,
    NORMAL,
    UNKNOWN,
    WARNING,
    DeviceHealthState,
    aggregate_health,
    extract_metric_statuses,
)
from app.services.agent_service import utc_now

logger = logging.getLogger(__name__)

# A device with no data for this long is considered OFFLINE (plan section 11).
OFFLINE_AFTER_SECONDS = 45

_OFFLINE = "OFFLINE"
_ONLINE = "ONLINE"


class HealthEngine:
    """In-memory anti-flap state per device plus database alert/event writes.

    State is process-local; after a server restart the first reports rebuild
    it and statuses re-commit within CONFIRMATION_SAMPLES cycles.
    """

    def __init__(self) -> None:
        self._devices: dict[int, DeviceHealthState] = {}

    def reset(self) -> None:
        """Drop in-memory state (used by tests and after manual DB resets)."""
        self._devices.clear()

    # -- incoming data ----------------------------------------------------

    def on_metrics(self, database: Session, device: Device, payload: dict) -> None:
        """Evaluate one snapshot, update health, and persist changes."""
        state = self._devices.setdefault(device.id, DeviceHealthState())
        statuses = extract_metric_statuses(payload)
        for metric, raw_status in statuses.items():
            change = state.feed(metric, raw_status)
            if change is not None:
                self._apply_metric_change(database, device, change)

        new_health = aggregate_health(state.committed_statuses())
        if device.health_status != new_health:
            device.health_status = new_health
            database.add(
                Event(
                    device_id=device.id,
                    event_type="HEALTH_CHANGED",
                    payload={"health": new_health},
                )
            )

        if device.connection_status != _ONLINE:
            self.mark_online(database, device)
        database.commit()

    def mark_online(self, database: Session, device: Device) -> None:
        """A heartbeat or snapshot from an offline device restores ONLINE."""
        was = device.connection_status
        device.connection_status = _ONLINE
        if was != _ONLINE:
            database.add(
                Event(
                    device_id=device.id,
                    event_type="DEVICE_ONLINE",
                    payload={"previous": was},
                )
            )

    # -- offline sweep ------------------------------------------------------

    def sweep_offline(self, database: Session) -> int:
        """Mark stale devices OFFLINE and log events. Returns updated count."""
        deadline = utc_now() - timedelta(seconds=OFFLINE_AFTER_SECONDS)
        stale = database.scalars(
            select(Device).where(
                Device.connection_status.not_in(("OFFLINE", "PENDING_APPROVAL")),
                Device.last_seen < deadline,
            )
        ).all()
        for device in stale:
            device.connection_status = _OFFLINE
            database.add(
                Event(
                    device_id=device.id,
                    event_type="DEVICE_OFFLINE",
                    payload={"last_seen": device.last_seen.isoformat()},
                )
            )
            self._devices.pop(device.id, None)
        if stale:
            database.commit()
            logger.info("Marked %d device(s) OFFLINE.", len(stale))
        return len(stale)

    # -- helpers -------------------------------------------------------------

    def _apply_metric_change(self, database: Session, device: Device, change) -> None:
        message = f"{change.metric.upper()}: {change.to_status}"
        if change.to_status in (WARNING, CRITICAL):
            database.add(
                Alert(
                    device_id=device.id,
                    severity=change.to_status,
                    message=message,
                    status="OPEN",
                )
            )
        elif change.to_status == NORMAL:
            self._resolve_alerts(database, device.id, change.metric)
        database.add(
            Event(
                device_id=device.id,
                event_type="METRIC_STATUS_CHANGED",
                payload={
                    "metric": change.metric,
                    "from": change.from_status or UNKNOWN,
                    "to": change.to_status,
                },
            )
        )

    @staticmethod
    def _resolve_alerts(database: Session, device_id: int, metric: str) -> None:
        prefix = f"{metric.upper()}:"
        open_alerts = database.scalars(
            select(Alert).where(
                Alert.device_id == device_id,
                Alert.status == "OPEN",
                Alert.message.startswith(prefix),
            )
        ).all()
        now = utc_now()
        for alert in open_alerts:
            alert.status = "RESOLVED"
            alert.resolved_at = now


# Single engine instance shared by the request handlers and the offline sweep.
engine = HealthEngine()

"""Read schemas for devices and stored metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer


def _utc_iso(value: datetime) -> str:
    """Serialize database datetimes (stored naive UTC) with an explicit offset."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class DeviceLatestSummary(BaseModel):
    """Current headline values extracted from the newest stored snapshot."""

    collected_at: datetime | None
    cpu_percent: float | None
    ram_percent: float | None
    disk_percent: float | None

    @field_serializer("collected_at")
    def _serialize_collected_at(self, value: datetime | None) -> str | None:
        return _utc_iso(value) if value is not None else None


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: str
    hostname: str
    ip_address: str | None
    os_name: str | None
    os_version: str | None
    agent_version: str
    connection_status: str
    health_status: str
    last_seen: datetime
    created_at: datetime
    updated_at: datetime
    latest: DeviceLatestSummary | None = None

    @field_serializer("last_seen", "created_at", "updated_at")
    def _serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value)


class MetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    schema_version: str
    collected_at: datetime | None
    received_at: datetime
    payload: dict[str, Any]

    @field_serializer("collected_at", "received_at")
    def _serialize_datetimes(self, value: datetime | None) -> str | None:
        return _utc_iso(value) if value is not None else None


class DeviceDeleteResponse(BaseModel):
    deleted_device_id: int
    message: str

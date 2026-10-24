"""Device retrieval and deletion service."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.metric import Metric
from app.schemas.device import DeviceLatestSummary, DeviceRead


class DeviceService:
    """Query devices and their stored raw metric snapshots."""

    @staticmethod
    def list_devices(database: Session) -> list[DeviceRead]:
        devices = database.scalars(select(Device).order_by(Device.id)).all()
        latest_metrics = DeviceService._latest_metric_per_device(database)
        result: list[DeviceRead] = []
        for device in devices:
            item = DeviceRead.model_validate(device)
            item.latest = DeviceService._summary_from_metric(latest_metrics.get(device.id))
            result.append(item)
        return result

    @staticmethod
    def get_device(database: Session, device_id: int) -> Device:
        device = database.get(Device, device_id)
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
        return device

    @staticmethod
    def get_metrics(database: Session, device_id: int, limit: int | None = None) -> list[Metric]:
        DeviceService.get_device(database, device_id)
        query = select(Metric).where(Metric.device_id == device_id).order_by(Metric.id.desc())
        if limit is not None:
            query = query.limit(limit)
        return list(database.scalars(query).all())

    @staticmethod
    def delete_device(database: Session, device_id: int) -> None:
        device = DeviceService.get_device(database, device_id)
        database.delete(device)
        database.commit()

    @staticmethod
    def _latest_metric_per_device(database: Session) -> dict[int, Metric]:
        latest_ids = select(func.max(Metric.id)).group_by(Metric.device_id).scalar_subquery()
        rows = database.scalars(select(Metric).where(Metric.id.in_(latest_ids))).all()
        return {metric.device_id: metric for metric in rows}

    @staticmethod
    def _summary_from_metric(metric: Metric | None) -> DeviceLatestSummary | None:
        """Read headline percentages from a raw payload without inventing values."""
        if metric is None:
            return None
        payload = metric.payload or {}
        cpu = payload.get("cpu") or {}
        ram = payload.get("ram") or {}
        disk = payload.get("disk") or {}
        partition_usages = [
            item.get("usage_percent")
            for item in disk.get("partitions") or []
            if isinstance(item, dict) and isinstance(item.get("usage_percent"), (int, float))
        ]
        return DeviceLatestSummary(
            collected_at=metric.collected_at,
            cpu_percent=_percent_or_none(cpu.get("usage_percent")),
            ram_percent=_percent_or_none(ram.get("usage_percent")),
            disk_percent=_percent_or_none(max(partition_usages)) if partition_usages else None,
        )


def _percent_or_none(value: object) -> float | None:
    return round(float(value), 1) if isinstance(value, (int, float)) else None

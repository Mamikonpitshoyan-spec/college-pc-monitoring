"""Read and delete routes for registered devices and stored snapshots."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.device import DeviceDeleteResponse, DeviceRead, MetricRead
from app.services.device_service import DeviceService

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=list[DeviceRead])
def list_devices(database: Session = Depends(get_db)) -> list[DeviceRead]:
    """Return registered devices with their newest headline metrics."""
    return DeviceService.list_devices(database)


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, database: Session = Depends(get_db)) -> DeviceRead:
    """Return one device by database id."""
    device = DeviceService.get_device(database, device_id)
    item = DeviceRead.model_validate(device)
    metrics = DeviceService.get_metrics(database, device_id, limit=1)
    item.latest = DeviceService._summary_from_metric(metrics[0]) if metrics else None
    return item


@router.get("/{device_id}/metrics", response_model=list[MetricRead])
def get_device_metrics(
    device_id: int,
    limit: int | None = Query(default=None, ge=1, le=1000),
    database: Session = Depends(get_db),
) -> list[MetricRead]:
    """Return raw snapshots, newest first, optionally limited to ``limit`` rows."""
    return DeviceService.get_metrics(database, device_id, limit=limit)


@router.delete("/{device_id}", response_model=DeviceDeleteResponse)
def delete_device(device_id: int, database: Session = Depends(get_db)) -> DeviceDeleteResponse:
    """Delete one device and its metrics; alert/event processing is not implemented."""
    DeviceService.delete_device(database, device_id)
    return DeviceDeleteResponse(deleted_device_id=device_id, message="Device deleted.")

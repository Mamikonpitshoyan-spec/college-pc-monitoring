"""Read routes for alerts and the event log (Level 9)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.alert import Alert
from app.models.event import Event

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    severity: str
    message: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    event_type: str
    payload: dict | None
    created_at: datetime


@router.get("/alerts", response_model=list[AlertRead])
def list_alerts(
    limit: int = Query(default=100, ge=1, le=1000),
    database: Session = Depends(get_db),
) -> list[AlertRead]:
    """Open and resolved alerts, newest first."""
    alerts = database.scalars(
        select(Alert).order_by(Alert.id.desc()).limit(limit)
    ).all()
    return [AlertRead.model_validate(alert) for alert in alerts]


@router.get("/events", response_model=list[EventRead])
def list_events(
    limit: int = Query(default=100, ge=1, le=1000),
    database: Session = Depends(get_db),
) -> list[EventRead]:
    """Event log entries, newest first."""
    events = database.scalars(
        select(Event).order_by(Event.id.desc()).limit(limit)
    ).all()
    return [EventRead.model_validate(event) for event in events]


@router.get("/config")
def monitoring_config(database: Session = Depends(get_db)) -> dict:
    """Non-secret runtime parameters shown on the Settings page."""
    from app.core.config import settings
    from app.monitoring.engine import OFFLINE_AFTER_SECONDS
    from app.monitoring.health import CONFIRMATION_SAMPLES

    from app.api.download import server_address

    address = server_address(database)
    return {
        "retention_hours": settings.metrics_retention_hours,
        "offline_after_seconds": OFFLINE_AFTER_SECONDS,
        "confirmation_samples": CONFIRMATION_SAMPLES,
        "dashboard_refresh_seconds": 5,
        "download_url": f"{address['url']}/download" if address["url"] else None,
    }


class ServerAddressUpdate(BaseModel):
    address: str | None = None


@router.get("/server-address")
def get_server_address(database: Session = Depends(get_db)) -> dict:
    """The single address shown to users (saved, else auto-detected) and the real port."""
    from app.api.download import server_address

    return server_address(database)


@router.put("/server-address")
def put_server_address(payload: ServerAddressUpdate, database: Session = Depends(get_db)) -> dict:
    """Save the admin-entered LAN address; empty → back to auto-detection."""
    import ipaddress
    import re

    from fastapi import HTTPException

    from app.api.download import save_address, server_address

    value = (payload.address or "").strip()
    value = re.sub(r"^https?://", "", value).split("/")[0].split(":")[0]
    if value:
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", value) or value.lower() == "localhost":
                raise HTTPException(status_code=422, detail="Invalid server address.")
        else:
            if ip.is_loopback or ip.is_unspecified:
                raise HTTPException(status_code=422, detail="Loopback address is not reachable from other PCs.")
    save_address(database, value or None)
    return server_address(database)

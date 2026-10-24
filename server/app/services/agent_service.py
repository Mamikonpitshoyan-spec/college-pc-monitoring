"""Device registration and heartbeat business logic."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device import Device
from app.schemas.agent import AgentRegistrationRequest, HeartbeatRequest
from app.services.security import generate_api_token, hash_api_token


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentService:
    """Keep route handlers free of registration and liveness persistence details."""

    @staticmethod
    def register(
        database: Session, payload: AgentRegistrationRequest
    ) -> tuple[Device, str | None, bool]:
        device = database.scalar(select(Device).where(Device.agent_id == payload.agent_id))
        now = utc_now()
        if device is not None:
            AgentService._apply_registration_metadata(device, payload, now)
            database.commit()
            database.refresh(device)
            return device, None, False

        api_token = generate_api_token()
        device = Device(
            agent_id=payload.agent_id,
            hostname=payload.hostname,
            ip_address=payload.ip_address,
            os_name=payload.os_name,
            os_version=payload.os_version,
            agent_version=payload.agent_version,
            connection_status="ONLINE",
            health_status="UNKNOWN",
            api_token_hash=hash_api_token(api_token),
            last_seen=now,
        )
        database.add(device)
        database.commit()
        database.refresh(device)
        return device, api_token, True

    @staticmethod
    def heartbeat(database: Session, device: Device, payload: HeartbeatRequest) -> Device:
        if device.agent_id != payload.agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token does not belong to agent_id.")
        device.last_seen = utc_now()
        from app.monitoring.engine import engine

        engine.mark_online(database, device)
        database.commit()
        database.refresh(device)
        return device

    @staticmethod
    def _apply_registration_metadata(
        device: Device, payload: AgentRegistrationRequest, seen_at: datetime
    ) -> None:
        device.hostname = payload.hostname
        device.ip_address = payload.ip_address
        device.os_name = payload.os_name
        device.os_version = payload.os_version
        device.agent_version = payload.agent_version
        device.last_seen = seen_at
        device.connection_status = "ONLINE"

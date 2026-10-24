"""Validated metrics persistence service."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.metric import Metric
from app.monitoring.engine import engine
from app.schemas.metrics import MetricsSubmission
from app.services.agent_service import utc_now


class MetricsService:
    """Persist raw v1.0 snapshots and evaluate device health (Level 9)."""

    @staticmethod
    def submit(database: Session, device: Device, payload: MetricsSubmission) -> Metric:
        if device.agent_id != payload.agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token does not belong to agent_id.")

        metric = Metric(
            device_id=device.id,
            schema_version=payload.schema_version,
            collected_at=payload.collected_at,
            payload=payload.payload_for_storage(),
        )
        device.last_seen = utc_now()
        device.connection_status = "ONLINE"
        database.add(metric)
        database.commit()
        database.refresh(metric)
        engine.on_metrics(database, device, payload.payload_for_storage())
        return metric

"""Agent registration, heartbeat, and metrics submission routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_registration_key
from app.database.session import get_db
from app.models.device import Device
from app.schemas.agent import (
    AgentRegistrationRequest,
    HeartbeatRequest,
    HeartbeatResponse,
    RegistrationResponse,
)
from app.schemas.metrics import MetricsSubmission, MetricsSubmissionResponse
from app.services.agent_service import AgentService
from app.services.metrics_service import MetricsService
from app.services.security import get_authenticated_device

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_agent(
    payload: AgentRegistrationRequest,
    _: None = Depends(verify_registration_key),
    database: Session = Depends(get_db),
) -> RegistrationResponse:
    """Create an agent device once, or update its registration metadata."""
    device, api_token, registered = AgentService.register(database, payload)
    return RegistrationResponse(
        device_id=device.id,
        agent_id=device.agent_id,
        registered=registered,
        message="Agent registered." if registered else "Agent already registered; metadata updated.",
        api_token=api_token,
    )


@router.post("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    payload: HeartbeatRequest,
    device: Device = Depends(get_authenticated_device),
    database: Session = Depends(get_db),
) -> HeartbeatResponse:
    """Update basic liveness only; offline and health aggregation are not Stage 3."""
    updated_device = AgentService.heartbeat(database, device, payload)
    return HeartbeatResponse(
        device_id=updated_device.id,
        agent_id=updated_device.agent_id,
        connection_status=updated_device.connection_status,
        last_seen=updated_device.last_seen.isoformat(),
    )


@router.post("/metrics", response_model=MetricsSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_metrics(
    payload: MetricsSubmission,
    device: Device = Depends(get_authenticated_device),
    database: Session = Depends(get_db),
) -> MetricsSubmissionResponse:
    """Validate and save one raw Stage 2 contract snapshot."""
    metric = MetricsService.submit(database, device, payload)
    return MetricsSubmissionResponse(
        metric_id=metric.id,
        device_id=metric.device_id,
        schema_version=metric.schema_version,
        message="Metrics accepted.",
    )

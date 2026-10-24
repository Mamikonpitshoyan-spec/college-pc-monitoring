"""Level 11 pairing routes: administrator actions and agent endpoints."""

from fastapi import APIRouter, Depends

from app.api.auth import require_admin_api
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.device import Device
from app.schemas.pairing import (
    PairingAttachRequest,
    PairingCreateResponse,
    PairingDeviceRead,
    PairingRecordRead,
    PairingStateResponse,
)
from app.services.pairing import full_code, pairing_service

router = APIRouter(tags=["pairing"])


def _full_code(database: Session, code: str) -> str:
    from urllib.parse import urlsplit

    from app.api.download import server_address

    info = server_address(database)
    host = urlsplit(info["url"]).hostname if info["url"] else None
    return full_code(code, host, info["port"])


def _record_read(database: Session, record) -> PairingRecordRead:
    device = database.get(Device, record.device_id) if record.device_id is not None else None
    return PairingRecordRead(
        code=record.code,
        full_code=_full_code(database, record.code),
        status=record.status,
        created_at=record.created_at,
        expires_at=record.expires_at,
        device=PairingDeviceRead.model_validate(device) if device else None,
    )


# ---------- administrator ----------

@router.post("/api/monitoring/pairing", response_model=PairingCreateResponse, status_code=201,
            dependencies=[Depends(require_admin_api)])
def create_pairing_code(database: Session = Depends(get_db)) -> PairingCreateResponse:
    """Generate a fresh one-time pairing code (valid 15 minutes)."""
    record = pairing_service.create_code()
    return PairingCreateResponse(
        code=record.code, full_code=_full_code(database, record.code), expires_at=record.expires_at
    )


@router.get("/api/monitoring/pairing", response_model=list[PairingRecordRead],
           dependencies=[Depends(require_admin_api)])
def list_pairing(database: Session = Depends(get_db)) -> list[PairingRecordRead]:
    """Active pairing codes with attached devices, for the admin dialog."""
    return [_record_read(database, record) for record in pairing_service.list_active()]


@router.post("/api/monitoring/pairing/{code}/approve", response_model=PairingStateResponse,
            dependencies=[Depends(require_admin_api)])
def approve_pairing(code: str, database: Session = Depends(get_db)) -> PairingStateResponse:
    """Approve the pending device; the agent receives its token on the next poll."""
    record = pairing_service.approve(database, code)
    return PairingStateResponse(status=record.status)


@router.post("/api/monitoring/pairing/{code}/reject", response_model=PairingStateResponse,
            dependencies=[Depends(require_admin_api)])
def reject_pairing(code: str, database: Session = Depends(get_db)) -> PairingStateResponse:
    """Reject the pending device and delete its row."""
    record = pairing_service.reject(database, code)
    return PairingStateResponse(status=record.status)


# ---------- agent ----------

@router.post("/api/agent/pair", response_model=PairingStateResponse)
def attach_pairing(payload: PairingAttachRequest, database: Session = Depends(get_db)) -> PairingStateResponse:
    """Submit identity with a pairing code; the device enters PENDING_APPROVAL."""
    record = pairing_service.attach(database, payload.pairing_code, payload.model_dump())
    return PairingStateResponse(status=record.status)


@router.get("/api/agent/pair/{code}/status", response_model=PairingStateResponse)
def pairing_status(code: str) -> PairingStateResponse:
    """Poll target: PENDING_APPROVAL until the admin decides, then the token."""
    record = pairing_service.peek(code)
    if record is None:
        return PairingStateResponse(status="EXPIRED")
    return PairingStateResponse(status=record.status, api_token=record.api_token)

"""Level 11 pairing: one-time codes and administrator approval.

Flow: the administrator creates a code (valid 15 minutes, single device) and
gives it to the user. The agent submits its identity with the code, the device
appears in PENDING_APPROVAL state, and the administrator either approves it
(the agent receives an API token on its next status poll) or rejects it
(the device row is deleted).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device import Device
from app.services.agent_service import utc_now
from app.services.security import generate_api_token, hash_api_token

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # без похожих символов (0/O, 1/I/L)
CODE_TTL_MINUTES = 15

WAITING = "WAITING"                     # код создан, устройство ещё не подключилось
PENDING_APPROVAL = "PENDING_APPROVAL"   # устройство представилось, ждёт решения админа
APPROVED = "APPROVED"                   # админ одобрил, токен выдан
REJECTED = "REJECTED"                   # админ отклонил


def generate_pairing_code() -> str:
    """Return a code like 'A7K-29P' without ambiguous characters."""
    def half() -> str:
        return "".join(secrets.choice(CODE_ALPHABET) for _ in range(3))
    return f"{half()}-{half()}"


ADDRESS_BASE_PORT = 8000
ADDRESS_PORT_SPAN = 32


def encode_address(host: str | None, port: int) -> str | None:
    """Pack an IPv4 server address + port into 8 code characters ('XXXX-XXXX').

    Variant B: the user types one string, the agent recovers the server
    address from it. Hostnames or ports outside 8000–8031 are not packed —
    the user app then asks for the address explicitly.
    """
    import ipaddress

    offset = port - ADDRESS_BASE_PORT
    if not host or not 0 <= offset < ADDRESS_PORT_SPAN:
        return None
    try:
        ip = ipaddress.IPv4Address(host)
    except ValueError:
        return None
    value = int(ip) * ADDRESS_PORT_SPAN + offset
    base = len(CODE_ALPHABET)
    chars = []
    for _ in range(8):
        value, digit = divmod(value, base)
        chars.append(CODE_ALPHABET[digit])
    packed = "".join(reversed(chars))
    return f"{packed[:4]}-{packed[4:]}"


def full_code(code: str, host: str | None, port: int) -> str:
    """The single string the admin hands out: 'A7K-29P-XXXX-XXXX' (or just the code)."""
    packed = encode_address(host, port)
    return f"{code}-{packed}" if packed else code


@dataclass
class PairingRecord:
    code: str
    created_at: Any
    expires_at: Any
    status: str = WAITING
    device_id: int | None = None
    api_token: str | None = None


class PairingService:
    """In-memory store of pairing codes (single uvicorn process).

    A server restart clears pending codes — the administrator simply creates
    a new one. Approved tokens live in the devices table, so restarts never
    break already-paired agents.
    """

    def __init__(self) -> None:
        self._codes: dict[str, PairingRecord] = {}

    def reset(self) -> None:
        self._codes.clear()

    def _get(self, code: str) -> PairingRecord | None:
        record = self._codes.get(code)
        if record is None:
            return None
        if record.status in (WAITING, PENDING_APPROVAL) and utc_now() > record.expires_at:
            del self._codes[code]
            return None
        return record

    def create_code(self) -> PairingRecord:
        """Generate a fresh single-use code."""
        self._cleanup_expired()
        code = generate_pairing_code()
        while code in self._codes:
            code = generate_pairing_code()
        now = utc_now()
        record = PairingRecord(
            code=code,
            created_at=now,
            expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
        )
        self._codes[code] = record
        return record

    def attach(self, database: Session, code: str, payload: dict[str, Any]) -> PairingRecord:
        """Agent identity submission with a pairing code (code = credential)."""
        record = self._get(code)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pairing code not found or expired.",
            )
        if record.status == REJECTED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This pairing code was rejected by the administrator.",
            )
        if record.status == APPROVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This pairing code has already been used.",
            )
        if record.status == PENDING_APPROVAL and record.device_id is not None:
            existing = database.get(Device, record.device_id)
            if existing is not None and existing.agent_id != payload["agent_id"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This code is already pending for another device.",
                )

        device = database.scalar(select(Device).where(Device.agent_id == payload["agent_id"]))
        now = utc_now()
        if device is None:
            device = Device(
                agent_id=payload["agent_id"],
                hostname=payload["hostname"],
                ip_address=payload.get("ip_address"),
                os_name=payload.get("os_name"),
                os_version=payload.get("os_version"),
                agent_version=payload.get("agent_version"),
                connection_status=PENDING_APPROVAL,
                health_status="UNKNOWN",
                api_token_hash="",  # токен выдаётся только после одобрения
                last_seen=now,
            )
        else:
            # Повторное сопряжение существующего устройства (например, после
            # потери токена): обновляем метаданные и снова ждём одобрения.
            device.hostname = payload["hostname"]
            device.ip_address = payload.get("ip_address")
            device.os_name = payload.get("os_name")
            device.os_version = payload.get("os_version")
            device.agent_version = payload.get("agent_version")
            device.connection_status = PENDING_APPROVAL
            device.last_seen = now
        database.add(device)
        database.commit()
        database.refresh(device)

        record.status = PENDING_APPROVAL
        record.device_id = device.id
        return record

    def approve(self, database: Session, code: str) -> PairingRecord:
        """Issue an API token to the pending device."""
        record = self._get(code)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing code not found or expired.")
        if record.status == APPROVED:
            return record
        if record.status != PENDING_APPROVAL or record.device_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No device has requested approval for this code yet.",
            )
        device = database.get(Device, record.device_id)
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
        token = generate_api_token()
        device.api_token_hash = hash_api_token(token)
        device.connection_status = "ONLINE"
        device.last_seen = utc_now()
        database.commit()
        record.status = APPROVED
        record.api_token = token
        return record

    def reject(self, database: Session, code: str) -> PairingRecord:
        """Remove the pending device and mark the code rejected."""
        record = self._get(code)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing code not found or expired.")
        if record.device_id is not None:
            device = database.get(Device, record.device_id)
            if device is not None:
                database.delete(device)
                database.commit()
        record.status = REJECTED
        record.device_id = None
        return record

    def list_active(self) -> list[PairingRecord]:
        """Active (non-expired) records, newest first."""
        self._cleanup_expired()
        return sorted(self._codes.values(), key=lambda r: r.created_at, reverse=True)

    def peek(self, code: str) -> PairingRecord | None:
        """Non-mutating lookup for the agent status poll (expired → None)."""
        return self._get(code)

    def _cleanup_expired(self) -> None:
        expired = [
            code for code, record in self._codes.items()
            if record.status in (WAITING, PENDING_APPROVAL) and utc_now() > record.expires_at
        ]
        for code in expired:
            del self._codes[code]


pairing_service = PairingService()

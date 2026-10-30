"""Pydantic schemas for pairing endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PairingCreateResponse(BaseModel):
    code: str
    full_code: str | None = None
    expires_at: datetime


class PairingDeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: str
    hostname: str
    ip_address: str | None
    agent_version: str


class PairingRecordRead(BaseModel):
    code: str
    full_code: str | None = None
    status: str
    created_at: datetime
    expires_at: datetime
    device: PairingDeviceRead | None = None


class PairingAttachRequest(BaseModel):
    """Agent identity submission with a pairing code (code = credential)."""

    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(pattern=r"^[A-Z0-9]{3}-[A-Z0-9]{3}$")
    agent_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: str | None = Field(default=None, max_length=45)
    os_name: str | None = Field(default=None, max_length=128)
    os_version: str | None = Field(default=None, max_length=255)
    agent_version: str = Field(min_length=1, max_length=64)
    schema_version: Literal["1.0"]


class PairingStateResponse(BaseModel):
    status: str
    api_token: str | None = None

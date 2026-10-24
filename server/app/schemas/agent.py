"""Pydantic schemas for agent registration and authenticated updates."""

from __future__ import annotations

import ipaddress
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AgentId = str


class AgentRegistrationRequest(BaseModel):
    """Initial or repeated registration metadata from an agent."""

    model_config = ConfigDict(extra="forbid")

    agent_id: AgentId = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: str | None = Field(default=None, max_length=45)
    os_name: str | None = Field(default=None, max_length=128)
    os_version: str | None = Field(default=None, max_length=255)
    agent_version: str = Field(min_length=1, max_length=64)
    schema_version: Literal["1.0"]

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        if value is not None:
            ipaddress.ip_address(value)
        return value


class HeartbeatRequest(BaseModel):
    """Authenticated liveness signal from a registered agent."""

    model_config = ConfigDict(extra="forbid")

    agent_id: AgentId = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")


class RegistrationResponse(BaseModel):
    """Token is populated only on a newly created registration."""

    device_id: int
    agent_id: AgentId
    registered: bool
    message: str
    api_token: str | None = None


class HeartbeatResponse(BaseModel):
    device_id: int
    agent_id: AgentId
    connection_status: str
    last_seen: str

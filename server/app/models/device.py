"""Registered monitoring agent device model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.event import Event
    from app.models.metric import Metric


class Device(Base):
    """A registered agent identity; agent_id is the stable external identifier."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    os_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_version: Mapped[str] = mapped_column(String(64), nullable=False)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ONLINE")
    health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    api_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    metrics: Mapped[list["Metric"]] = relationship(
        back_populates="device", cascade="all, delete-orphan", passive_deletes=True
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="device")
    events: Mapped[list["Event"]] = relationship(back_populates="device")

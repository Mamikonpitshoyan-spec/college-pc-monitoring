"""Validation that preserves the Stage 2 metrics JSON contract."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MetricsSubmission(BaseModel):
    """An agent envelope plus arbitrary JSON metric sections from contract v1.0."""

    model_config = ConfigDict(extra="allow")

    agent_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
    schema_version: Literal["1.0"]
    collected_at: datetime

    @model_validator(mode="after")
    def validate_metric_payload(self) -> "MetricsSubmission":
        """Reject non-JSON/non-finite data while retaining unknown future sections."""
        for section_name, value in (self.model_extra or {}).items():
            if section_name in {"cpu", "ram", "disk", "network", "gpu", "temperature", "system", "bios", "ports"}:
                if value is not None and not isinstance(value, dict):
                    raise ValueError(f"{section_name} must be an object or null")
            self._validate_json_value(value, section_name)
        return self

    @classmethod
    def _validate_json_value(cls, value: Any, location: str) -> None:
        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float):
            if not isfinite(value):
                raise ValueError(f"{location} contains a non-finite number")
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                cls._validate_json_value(item, f"{location}[{index}]")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"{location} contains a non-string key")
                cls._validate_json_value(item, f"{location}.{key}")
            return
        raise ValueError(f"{location} contains a non-JSON value")

    def payload_for_storage(self) -> dict[str, Any]:
        """Return the complete validated request in JSON-compatible form."""
        return self.model_dump(mode="json")


class MetricsSubmissionResponse(BaseModel):
    metric_id: int
    device_id: int
    schema_version: Literal["1.0"]
    message: str

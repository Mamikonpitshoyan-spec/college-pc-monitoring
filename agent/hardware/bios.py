"""BIOS/UEFI and motherboard data through documented Windows CIM classes."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from hardware.windows import WindowsCimClient

_WMI_DATE = re.compile(r"^/Date\((-?\d+)\)/$")


class BiosCollector:
    """Collect only information that Windows exposes through management APIs."""

    def __init__(self, cim_client: WindowsCimClient) -> None:
        self._cim_client = cim_client

    def collect(self) -> dict[str, Any]:
        bios = self._cim_client.query_one(
            "Win32_BIOS",
            ("Manufacturer", "SMBIOSBIOSVersion", "ReleaseDate", "SerialNumber"),
        )
        baseboard = self._cim_client.query_one(
            "Win32_BaseBoard",
            ("Manufacturer", "Product", "Version", "SerialNumber"),
        )
        return {
            "manufacturer": self._value(bios, "Manufacturer"),
            "version": self._value(bios, "SMBIOSBIOSVersion"),
            "release_date": self._wmi_date_to_iso(self._value(bios, "ReleaseDate")),
            "serial_number": self._value(bios, "SerialNumber"),
            "motherboard": {
                "manufacturer": self._value(baseboard, "Manufacturer"),
                "model": self._value(baseboard, "Product"),
                "version": self._value(baseboard, "Version"),
                "serial_number": self._value(baseboard, "SerialNumber"),
            },
        }

    @staticmethod
    def _wmi_date_to_iso(value: Any | None) -> str | None:
        """Convert the PowerShell `/Date(ms)/` JSON form to an ISO-8601 UTC string."""
        if not isinstance(value, str):
            return value
        match = _WMI_DATE.match(value)
        if match is None:
            return value
        try:
            moment = datetime.fromtimestamp(int(match.group(1)) / 1000, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
        return moment.date().isoformat()

    @staticmethod
    def _value(source: dict[str, Any] | None, key: str) -> Any | None:
        return source.get(key) if source else None

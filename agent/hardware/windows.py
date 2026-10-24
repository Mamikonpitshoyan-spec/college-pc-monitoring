"""Minimal Windows CIM access through the built-in PowerShell host."""

from __future__ import annotations

import json
import logging
import platform
import subprocess
from typing import Any, Iterable

logger = logging.getLogger(__name__)


class WindowsCimClient:
    """Read available Windows management data without treating BIOS as a file."""

    _TIMEOUT_SECONDS = 10

    def query_one(
        self,
        class_name: str,
        properties: Iterable[str],
        timeout_seconds: int | None = None,
    ) -> dict[str, Any] | None:
        """Return the first CIM instance, or null when it cannot be obtained."""
        records = self.query(class_name, properties, timeout_seconds)
        return records[0] if records else None

    def query(
        self,
        class_name: str,
        properties: Iterable[str],
        timeout_seconds: int | None = None,
    ) -> list[dict[str, Any]] | None:
        """Run a constrained CIM query and parse PowerShell's JSON result."""
        if platform.system() != "Windows":
            logger.warning("Windows CIM data is unavailable on %s", platform.system())
            return None

        selected_properties = ", ".join(properties)
        script = (
            "$ErrorActionPreference = 'Stop'; "
            f"Get-CimInstance -ClassName {class_name} | "
            f"Select-Object -Property {selected_properties} | "
            "ConvertTo-Json -Compress -Depth 4"
        )
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds or self._TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            logger.warning("CIM query for %s failed: %s", class_name, error)
            return None

        if completed.returncode != 0:
            logger.warning(
                "CIM query for %s returned %s: %s",
                class_name,
                completed.returncode,
                completed.stderr.strip(),
            )
            return None
        if not completed.stdout.strip():
            return []

        try:
            raw_result = json.loads(completed.stdout.lstrip("\ufeff"))
        except json.JSONDecodeError as error:
            logger.warning("CIM query for %s returned invalid JSON: %s", class_name, error)
            return None

        if isinstance(raw_result, dict):
            return [raw_result]
        if isinstance(raw_result, list) and all(
            isinstance(record, dict) for record in raw_result
        ):
            return raw_result
        logger.warning("CIM query for %s returned an unexpected JSON shape", class_name)
        return None

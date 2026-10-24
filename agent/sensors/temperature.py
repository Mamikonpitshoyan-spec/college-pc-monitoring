"""Optional temperature sensor layer with several real data sources.

Sources are tried in order; the first one that returns plausible readings wins:
1. psutil sensors (Linux/POSIX; does not exist on Windows).
2. LibreHardwareMonitor web endpoint (needs a one-time elevated start of LHM).
3. ACPI thermal zones via WMI ``root/wmi`` (needs the agent to run elevated).
4. Windows thermal-zone performance counters (no extra program, no elevation).
NVIDIA GPU temperatures from nvidia-smi are appended when present.

When every source is unavailable the section stays ``null`` — values are
never invented.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from typing import Any, Callable

import httpx
import psutil

from config.settings import settings

logger = logging.getLogger(__name__)

_VALUE_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")
_MIN_PLAUSIBLE_CELSIUS = -20.0
_MAX_PLAUSIBLE_CELSIUS = 150.0


class TemperatureCollector:
    """Return real sensor values from the best available Windows source."""

    def __init__(self, lhm_get: Callable[[str], httpx.Response | None] | None = None) -> None:
        self._lhm_get = lhm_get
        self._lhm_unreachable = False

    def collect(self) -> dict[str, Any]:
        readings = (
            self._psutil_readings() or self._lhm_readings() or self._acpi_readings()
            or self._perf_counter_readings()
        )
        readings = list(readings) + self._nvidia_readings()
        return {"unit": "celsius", "sensors": readings or None}

    # -- source 4: thermal-zone performance counters ----------------------

    def _perf_counter_readings(self) -> list[dict[str, Any]]:
        script = (
            "$ErrorActionPreference = 'Stop'; "
            "Get-CimInstance -ClassName Win32_PerfFormattedData_Counters_ThermalZoneInformation "
            "| Select-Object -Property Name, HighPrecisionTemperature "
            "| ConvertTo-Json -Compress -Depth 3"
        )
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, check=False, encoding="utf-8", errors="replace",
                timeout=10, creationflags=0x08000000,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            logger.info("Thermal-zone counters query failed: %s", error)
            return []
        if completed.returncode != 0 or not completed.stdout.strip():
            return []
        try:
            records = json.loads(completed.stdout.lstrip("\ufeff"))
        except ValueError:
            return []
        if isinstance(records, dict):
            records = [records]
        readings = []
        for record in records:
            celsius = _tenths_kelvin_to_celsius(record.get("HighPrecisionTemperature"))
            if celsius is None:
                continue
            readings.append({
                "chip": "thermal-zone",
                "label": record.get("Name") or None,
                "current_celsius": celsius,
                "high_celsius": None,
                "critical_celsius": None,
            })
        return readings

    # -- NVIDIA GPU via nvidia-smi ----------------------------------------

    @staticmethod
    def _nvidia_readings() -> list[dict[str, Any]]:
        from hardware.gpu import query_nvidia_gpus

        return [
            {
                "chip": "nvidia-gpu",
                "label": gpu["name"],
                "current_celsius": gpu["temperature_celsius"],
                "high_celsius": None,
                "critical_celsius": None,
            }
            for gpu in query_nvidia_gpus()
            if gpu.get("temperature_celsius") is not None
        ]

    # -- source 1: psutil -------------------------------------------------

    def _psutil_readings(self) -> list[dict[str, Any]]:
        try:
            temperatures = psutil.sensors_temperatures(fahrenheit=False)
        except (AttributeError, NotImplementedError, OSError) as error:
            logger.info("psutil temperature sensors are unavailable: %s", error)
            return []
        readings: list[dict[str, Any]] = []
        for chip, entries in (temperatures or {}).items():
            for entry in entries:
                readings.append(
                    {
                        "chip": chip,
                        "label": entry.label or None,
                        "current_celsius": entry.current,
                        "high_celsius": entry.high,
                        "critical_celsius": entry.critical,
                    }
                )
        return readings

    # -- source 2: LibreHardwareMonitor web server ------------------------

    def _lhm_readings(self) -> list[dict[str, Any]]:
        """Read /data.json from LibreHardwareMonitor (Option → Web Server)."""
        if self._lhm_unreachable:
            return []
        try:
            response = (
                self._lhm_get(settings.lhm_url)
                if self._lhm_get
                else httpx.get(settings.lhm_url, timeout=1.5)
            )
        except (httpx.HTTPError, OSError):
            self._lhm_unreachable = True
            logger.info(
                "LibreHardwareMonitor is not reachable at %s; skipping it.",
                settings.lhm_url,
            )
            return []
        if response is None or response.status_code != 200:
            self._lhm_unreachable = True
            return []

        readings: list[dict[str, Any]] = []
        _walk_temperature_nodes(response.json(), "", readings)
        self._lhm_unreachable = False
        return readings

    # -- source 3: ACPI thermal zones through WMI --------------------------

    def _acpi_readings(self) -> list[dict[str, Any]]:
        script = (
            "$ErrorActionPreference = 'Stop'; "
            "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
            "| Select-Object -Property InstanceName, CurrentTemperature "
            "| ConvertTo-Json -Compress -Depth 3"
        )
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            logger.info("ACPI thermal zone query failed: %s", error)
            return []
        if completed.returncode != 0 or not completed.stdout.strip():
            logger.info(
                "ACPI thermal zones are unavailable (administrator rights or driver support required)."
            )
            return []

        try:
            records = json.loads(completed.stdout.lstrip("\ufeff"))
        except ValueError:
            logger.info(
                "ACPI thermal zone output was not valid JSON: %.200s", completed.stdout
            )
            return []
        if isinstance(records, dict):
            records = [records]

        readings: list[dict[str, Any]] = []
        for record in records:
            celsius = _tenths_kelvin_to_celsius(record.get("CurrentTemperature"))
            if celsius is None:
                logger.info(
                    "ACPI thermal zone %s gave an unusable value %r; skipping.",
                    record.get("InstanceName"),
                    record.get("CurrentTemperature"),
                )
                continue
            readings.append(
                {
                    "chip": "acpi-thermal-zone",
                    "label": record.get("InstanceName") or None,
                    "current_celsius": celsius,
                    "high_celsius": None,
                    "critical_celsius": None,
                }
            )
        if not readings:
            logger.info(
                "ACPI thermal zones returned no plausible temperatures: %.300s",
                completed.stdout,
            )
        return readings


def _tenths_kelvin_to_celsius(raw: Any) -> float | None:
    """Convert ACPI tenths-of-Kelvin to Celsius; reject implausible values."""
    if isinstance(raw, str):
        raw = raw.strip()
        try:
            raw = float(raw)
        except ValueError:
            return None
    if not isinstance(raw, (int, float)):
        return None
    celsius = float(raw) / 10.0 - 273.15
    if not _MIN_PLAUSIBLE_CELSIUS <= celsius <= _MAX_PLAUSIBLE_CELSIUS:
        return None
    return round(celsius, 1)


def _walk_temperature_nodes(node: Any, path: str, out: list[dict[str, Any]]) -> None:
    """Collect temperature sensor nodes from the LibreHardwareMonitor JSON tree."""
    if not isinstance(node, dict):
        return
    node_id = str(node.get("id") or node.get("Id") or "")
    if "/temperature/" in node_id:
        value = _parse_sensor_number(node.get("Value"))
        if value is not None:
            out.append(
                {
                    "chip": _chip_from_path(node_id),
                    "label": node.get("Text") or node.get("text") or None,
                    "current_celsius": value,
                    "high_celsius": None,
                    "critical_celsius": None,
                }
            )
    for child in node.get("Children") or node.get("children") or []:
        _walk_temperature_nodes(child, node_id, out)


def _chip_from_path(sensor_id: str) -> str | None:
    parts = [part for part in sensor_id.split("/") if part]
    return parts[0] if parts else None


def _parse_sensor_number(raw: Any) -> float | None:
    """Parse values like ``'45.5 °C'`` or plain numbers."""
    if isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str):
        match = _VALUE_NUMBER.search(raw)
        if match is None:
            return None
        value = float(match.group(0).replace(",", "."))
    else:
        return None
    if not _MIN_PLAUSIBLE_CELSIUS <= value <= _MAX_PLAUSIBLE_CELSIUS:
        return None
    return round(value, 1)

"""GPU collector architecture backed only by available native Windows data."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hardware.windows import WindowsCimClient

logger = logging.getLogger(__name__)

_DISPLAY_CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
_NO_WINDOW = 0x08000000


def _nvidia_smi_path() -> str | None:
    found = shutil.which("nvidia-smi")
    if found:
        return found
    fallback = Path("C:/Windows/System32/nvidia-smi.exe")
    return str(fallback) if fallback.exists() else None


def _number(raw: str) -> float | None:
    try:
        return float(raw.strip())
    except ValueError:
        return None  # "[N/A]", "[Not Supported]"


def query_nvidia_gpus() -> list[dict[str, Any]]:
    """Real NVIDIA readings via nvidia-smi; [] when there is no NVIDIA driver."""
    executable = _nvidia_smi_path()
    if executable is None:
        return []
    try:
        completed = subprocess.run(
            [executable, "--query-gpu=name,memory.total,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=5,
            check=False, creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        logger.info("nvidia-smi is unavailable: %s", error)
        return []
    if completed.returncode != 0:
        return []
    gpus = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4 or not parts[0]:
            continue
        memory_mib = _number(parts[1])
        gpus.append({
            "name": parts[0],
            "memory_bytes": int(memory_mib * 1024 * 1024) if memory_mib is not None else None,
            "usage_percent": _number(parts[2]),
            "temperature_celsius": _number(parts[3]),
        })
    return gpus


def registry_gpu_memory() -> dict[str, int]:
    """Dedicated VRAM per adapter name from the display driver registry (64-bit value).

    Win32_VideoController.AdapterRAM is a 32-bit field capped at 4 GB.
    """
    try:
        import winreg
    except ImportError:
        return {}
    memory: dict[str, int] = {}
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _DISPLAY_CLASS_KEY)
    except OSError:
        return {}
    with root:
        index = 0
        while True:
            try:
                sub_name = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1
            try:
                with winreg.OpenKey(root, sub_name) as sub:
                    name = winreg.QueryValueEx(sub, "DriverDesc")[0]
                    try:
                        raw = winreg.QueryValueEx(sub, "HardwareInformation.qwMemorySize")[0]
                    except OSError:
                        raw = winreg.QueryValueEx(sub, "HardwareInformation.MemorySize")[0]
            except OSError:
                continue
            if isinstance(raw, bytes):
                raw = int.from_bytes(raw[:8], "little")
            if isinstance(raw, int) and raw > 0 and isinstance(name, str):
                memory[name] = raw
    return memory


class GpuCollector:
    """Expose discovered adapters without inventing utilisation or temperature values."""

    def __init__(self, cim_client: WindowsCimClient) -> None:
        self._cim_client = cim_client

    def collect(self) -> dict[str, Any]:
        adapters = self._cim_client.query(
            "Win32_VideoController",
            ("Name", "AdapterCompatibility", "DriverVersion", "AdapterRAM"),
            timeout_seconds=3,
        )
        if adapters is None:
            return {"adapters": None}
        vram = registry_gpu_memory()
        nvidia = {gpu["name"]: gpu for gpu in query_nvidia_gpus()}
        result = []
        for adapter in adapters:
            name = adapter.get("Name")
            smi = nvidia.get(name) or {}
            result.append(
                {
                    "name": name,
                    "manufacturer": adapter.get("AdapterCompatibility"),
                    "driver_version": adapter.get("DriverVersion"),
                    # Реестр/nvidia-smi; AdapterRAM упирается в 4 ГБ — только если других нет.
                    "adapter_ram_bytes": vram.get(name) or smi.get("memory_bytes") or adapter.get("AdapterRAM"),
                    "usage_percent": smi.get("usage_percent"),
                    "temperature_celsius": smi.get("temperature_celsius"),
                }
            )
        # [] = видеокарта не обнаружена; None = данных нет.
        return {"adapters": result}

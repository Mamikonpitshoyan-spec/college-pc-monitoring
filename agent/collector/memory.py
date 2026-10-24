"""RAM metrics from psutil."""

from __future__ import annotations

from typing import Any

import psutil


class MemoryCollector:
    """Collect virtual-memory capacity and current use."""

    def collect(self) -> dict[str, Any]:
        memory = psutil.virtual_memory()
        return {
            "total_bytes": memory.total,
            "used_bytes": memory.used,
            "available_bytes": memory.available,
            "usage_percent": memory.percent,
        }

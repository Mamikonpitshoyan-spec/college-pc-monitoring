"""Local status file for the user-facing status app (Level 12 UX).

The reporting loop merges its full status into ``status.json`` after every
cycle attempt, and a fast sampler thread refreshes headline cpu/ram every
couple of seconds so the user app feels live. Writes are atomic
(tmp + replace) and serialized with a lock — one writer process, many readers.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StatusWriter:
    """Merge-and-write store for the latest agent status snapshot."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}

    def update(self, data: dict[str, Any]) -> None:
        """Merge ``data`` over the current status and write atomically."""
        with self._lock:
            self._data.update(data)
            self._write()

    # Backward-compatible alias for the reporting callback.
    write = update

    def _write(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self._data, ensure_ascii=False, indent=2)
            handle, tmp_name = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as tmp_file:
                    tmp_file.write(payload)
                os.replace(tmp_name, self._path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
        except OSError:
            logger.warning("Unable to write local status file %s.", self._path, exc_info=True)

    @staticmethod
    def empty(server_url: str, agent_id: str | None, hostname: str | None) -> dict[str, Any]:
        return {
            "updated_at": None,
            "connected": False,
            "agent_id": agent_id,
            "hostname": hostname,
            "server_url": server_url,
            "last_report_at": None,
            "last_error": None,
            "cpu_percent": None,
            "ram_percent": None,
            "disk_percent": None,
        }


def start_fast_sampler(writer: StatusWriter, stop_event: threading.Event | None = None,
                       interval: float = 2.0) -> threading.Thread:
    """Live headline metrics between full collection cycles.

    psutil's non-blocking cpu_percent returns the usage since the previous
    call, so the thread primes it once and then samples every ``interval``
    seconds. This makes the user app update in real time while the slow
    WMI/CIM collection keeps its own schedule.
    """
    import psutil
    import time as time_module

    psutil.cpu_percent(interval=None)  # prime the counter

    def loop() -> None:
        while stop_event is None or not stop_event.is_set():
            writer.update(
                {
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "ram_percent": psutil.virtual_memory().percent,
                    "updated_at": time_module.strftime("%Y-%m-%dT%H:%M:%S"),
                }
            )
            if stop_event is not None:
                stop_event.wait(interval)
            else:
                time_module.sleep(interval)

    thread = threading.Thread(target=loop, daemon=True, name="fast-status-sampler")
    thread.start()
    return thread

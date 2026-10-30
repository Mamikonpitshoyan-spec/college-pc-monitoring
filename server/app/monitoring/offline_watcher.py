"""Background loop: offline sweep and history retention."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import settings
from app.database.session import SessionLocal
from app.monitoring.engine import engine
from app.monitoring.retention import prune_old_metrics

logger = logging.getLogger(__name__)

_SWEEP_INTERVAL_SECONDS = 10
_PRUNE_INTERVAL_SECONDS = 30 * 60


async def offline_sweeper() -> None:
    """Periodically sweep offline devices and prune old metric history."""
    last_prune = 0.0
    while True:
        try:
            database = SessionLocal()
            try:
                engine.sweep_offline(database)
                if time.monotonic() - last_prune >= _PRUNE_INTERVAL_SECONDS:
                    prune_old_metrics(database, settings.metrics_retention_hours)
                    last_prune = time.monotonic()
            finally:
                database.close()
        except Exception:
            logger.exception("Background maintenance failed; retrying next cycle.")
        await asyncio.sleep(_SWEEP_INTERVAL_SECONDS)

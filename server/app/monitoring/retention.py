"""Retention: keep the metrics history bounded."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.metric import Metric
from app.services.agent_service import utc_now

logger = logging.getLogger(__name__)


def prune_old_metrics(database: Session, retention_hours: int) -> int:
    """Delete snapshots older than the retention window. Returns removed count."""
    # SQLite stores naive UTC; compare against a naive cutoff for correctness.
    cutoff = (utc_now() - timedelta(hours=retention_hours)).replace(tzinfo=None)
    result = database.execute(delete(Metric).where(Metric.collected_at < cutoff))
    database.commit()
    removed = result.rowcount or 0
    if removed:
        logger.info("Retention: removed %d metric snapshot(s) older than %d h.", removed, retention_hours)
    return removed

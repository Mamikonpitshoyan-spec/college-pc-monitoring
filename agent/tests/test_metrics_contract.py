"""Tests for the stable metrics envelope."""

import unittest

from collector.metrics import METRICS_SCHEMA_VERSION, MetricsSnapshot


class MetricsSnapshotTests(unittest.TestCase):
    def test_snapshot_serialises_all_metric_sections(self) -> None:
        snapshot = MetricsSnapshot(
            schema_version=METRICS_SCHEMA_VERSION,
            collected_at="2026-01-01T00:00:00+00:00",
            cpu=None,
            ram=None,
            disk=None,
            network=None,
            gpu=None,
            temperature=None,
            system=None,
            bios=None,
        )

        result = snapshot.to_dict()

        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(
            set(result),
            {
                "schema_version",
                "collected_at",
                "cpu",
                "ram",
                "disk",
                "network",
                "gpu",
                "temperature",
                "system",
                "bios",
                "ports",
            },
        )

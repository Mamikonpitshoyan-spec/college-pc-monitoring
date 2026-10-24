"""Unit tests for Level 9 health logic (thresholds + anti-flapping)."""

import unittest

from app.monitoring.health import (
    CRITICAL,
    NORMAL,
    UNKNOWN,
    WARNING,
    DeviceHealthState,
    aggregate_health,
    classify_percent,
    extract_metric_statuses,
)


class ClassifyTests(unittest.TestCase):
    def test_cpu_ram_thresholds(self) -> None:
        self.assertEqual(classify_percent(79.9, {"warning": 80, "critical": 95}), NORMAL)
        self.assertEqual(classify_percent(80.0, {"warning": 80, "critical": 95}), WARNING)
        self.assertEqual(classify_percent(94.9, {"warning": 80, "critical": 95}), WARNING)
        self.assertEqual(classify_percent(95.0, {"warning": 80, "critical": 95}), CRITICAL)

    def test_unavailable_value_is_none(self) -> None:
        self.assertIsNone(classify_percent(None, {"warning": 80, "critical": 95}))
        self.assertIsNone(classify_percent("80", {"warning": 80, "critical": 95}))

    def test_extract_reads_disk_worst_partition(self) -> None:
        statuses = extract_metric_statuses(
            {
                "cpu": {"usage_percent": 10},
                "ram": {"usage_percent": 50},
                "disk": {
                    "partitions": [
                        {"usage_percent": 40},
                        {"usage_percent": 96},
                    ]
                },
            }
        )
        self.assertEqual(statuses["cpu"], NORMAL)
        self.assertEqual(statuses["ram"], NORMAL)
        self.assertEqual(statuses["disk"], CRITICAL)


class AggregateTests(unittest.TestCase):
    def test_worst_status_wins(self) -> None:
        self.assertEqual(aggregate_health([NORMAL, NORMAL]), NORMAL)
        self.assertEqual(aggregate_health([NORMAL, WARNING, NORMAL]), WARNING)
        self.assertEqual(aggregate_health([WARNING, CRITICAL]), CRITICAL)

    def test_no_data_is_unknown(self) -> None:
        self.assertEqual(aggregate_health([]), UNKNOWN)
        self.assertEqual(aggregate_health([None, None]), UNKNOWN)


class AntiFlapTests(unittest.TestCase):
    def test_status_commits_only_after_three_samples(self) -> None:
        state = DeviceHealthState()
        self.assertIsNone(state.feed("cpu", WARNING))
        self.assertIsNone(state.feed("cpu", WARNING))
        change = state.feed("cpu", WARNING)
        self.assertIsNotNone(change)
        self.assertEqual(change.to_status, WARNING)
        self.assertEqual(change.from_status, None)

    def test_single_spike_never_commits(self) -> None:
        state = DeviceHealthState()
        # Плановый пример: 79 / 81 / 79 не должно переключать CPU во WARNING.
        for value in [NORMAL, WARNING, NORMAL, WARNING, NORMAL]:
            self.assertIsNone(state.feed("cpu", value))
        self.assertEqual(state.committed_statuses(), [])

    def test_recovery_also_needs_three_samples(self) -> None:
        state = DeviceHealthState()
        for _ in range(3):
            state.feed("cpu", CRITICAL)
        self.assertIsNone(state.feed("cpu", NORMAL))
        self.assertIsNone(state.feed("cpu", NORMAL))
        change = state.feed("cpu", NORMAL)
        self.assertEqual(change.to_status, NORMAL)

    def test_alternating_never_commits(self) -> None:
        state = DeviceHealthState()
        for _ in range(10):
            self.assertIsNone(state.feed("ram", CRITICAL))
            self.assertIsNone(state.feed("ram", WARNING))
        self.assertEqual(state.committed_statuses(), [])


if __name__ == "__main__":
    unittest.main()

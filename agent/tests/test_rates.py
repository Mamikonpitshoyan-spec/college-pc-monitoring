"""Tests for delta/time throughput calculation."""

import unittest

from collector.rates import ByteCounters, ByteRateTracker


class ByteRateTrackerTests(unittest.TestCase):
    def test_first_observation_is_a_baseline(self) -> None:
        tracker = ByteRateTracker()

        rates = tracker.sample({"Ethernet": ByteCounters(100, 200)}, timestamp=10.0)

        self.assertIsNone(rates["Ethernet"].inbound_Bps)
        self.assertIsNone(rates["Ethernet"].outbound_Bps)

    def test_second_observation_uses_delta_divided_by_elapsed_time(self) -> None:
        tracker = ByteRateTracker()
        tracker.sample({"Ethernet": ByteCounters(100, 200)}, timestamp=10.0)

        rates = tracker.sample({"Ethernet": ByteCounters(160, 260)}, timestamp=12.0)

        self.assertEqual(rates["Ethernet"].inbound_Bps, 30.0)
        self.assertEqual(rates["Ethernet"].outbound_Bps, 30.0)

    def test_counter_reset_does_not_create_negative_speed(self) -> None:
        tracker = ByteRateTracker()
        tracker.sample({"Ethernet": ByteCounters(100, 200)}, timestamp=10.0)

        rates = tracker.sample({"Ethernet": ByteCounters(5, 6)}, timestamp=12.0)

        self.assertIsNone(rates["Ethernet"].inbound_Bps)
        self.assertIsNone(rates["Ethernet"].outbound_Bps)

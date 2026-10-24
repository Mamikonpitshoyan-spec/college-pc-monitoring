"""Unit tests for the multi-source temperature layer."""

import unittest
from unittest import mock

from httpx import Response

from sensors.temperature import (
    TemperatureCollector,
    _parse_sensor_number,
    _tenths_kelvin_to_celsius,
    _walk_temperature_nodes,
)

_LHM_TREE = {
    "id": "0",
    "Text": "root",
    "Children": [
        {
            "id": "/0/cpu/0",
            "Text": "Intel CPU",
            "Children": [
                {"id": "/0/cpu/0/temperature/0", "Text": "CPU Package", "Value": "45.5 °C"},
                {"id": "/0/cpu/0/temperature/1", "Text": "CPU Core #1", "Value": "43,0 °C"},
                {"id": "/0/cpu/0/load/0", "Text": "CPU Total", "Value": "12.0 %"},
            ],
        },
        {"id": "/1/board/0/temperature/0", "Text": "Temperature #1", "Value": "37.0 °C"},
    ],
}


class TemperatureConversionTests(unittest.TestCase):
    def test_tenths_kelvin_to_celsius(self) -> None:
        self.assertEqual(_tenths_kelvin_to_celsius(3010), 27.9)
        self.assertEqual(_tenths_kelvin_to_celsius(3180), 44.9)

    def test_implausible_values_rejected(self) -> None:
        self.assertIsNone(_tenths_kelvin_to_celsius(0))
        self.assertIsNone(_tenths_kelvin_to_celsius(-50))
        self.assertIsNone(_tenths_kelvin_to_celsius("not-a-number"))

    def test_numeric_strings_are_accepted(self) -> None:
        # ConvertTo-Json may deliver WMI UInt32 values as strings.
        self.assertEqual(_tenths_kelvin_to_celsius("3010"), 27.9)
        self.assertEqual(_tenths_kelvin_to_celsius(" 3010 "), 27.9)

    def test_parse_sensor_number(self) -> None:
        self.assertEqual(_parse_sensor_number("45.5 °C"), 45.5)
        self.assertEqual(_parse_sensor_number("43,0 °C"), 43.0)
        self.assertEqual(_parse_sensor_number(51), 51.0)
        self.assertIsNone(_parse_sensor_number("n/a"))

    def test_walk_collects_only_temperature_nodes(self) -> None:
        out: list = []
        _walk_temperature_nodes(_LHM_TREE, "", out)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["label"], "CPU Package")
        self.assertEqual(out[0]["current_celsius"], 45.5)
        self.assertEqual(out[1]["current_celsius"], 43.0)
        self.assertEqual(out[2]["chip"], "1")


class TemperatureCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        # Реальные источники этого ПК (ACPI, счётчики, nvidia-smi) в тестах не опрашиваем.
        for name in ("_acpi_readings", "_perf_counter_readings", "_nvidia_readings"):
            patcher = mock.patch.object(TemperatureCollector, name, return_value=[])
            patcher.start()
            self.addCleanup(patcher.stop)

    def _collector(self, lhm_payload: object | None) -> TemperatureCollector:
        def fake_get(url: str) -> Response | None:
            if lhm_payload is None:
                raise ConnectionError("LHM not running")
            return Response(200, json=lhm_payload)

        return TemperatureCollector(lhm_get=fake_get)

    def test_psutil_unreachable_and_lhm_absent_gives_null(self) -> None:
        with mock.patch("psutil.sensors_temperatures", side_effect=AttributeError, create=True):
            result = self._collector(None).collect()
        self.assertEqual(result, {"unit": "celsius", "sensors": None})

    def test_lhm_source_used_when_available(self) -> None:
        with mock.patch("psutil.sensors_temperatures", side_effect=AttributeError, create=True):
            result = self._collector(_LHM_TREE).collect()
        self.assertEqual(len(result["sensors"]), 3)

    def test_psutil_source_wins_when_present(self) -> None:
        psutil_entry = mock.Mock(label="core", current=55.0, high=85.0, critical=100.0)
        with mock.patch(
            "psutil.sensors_temperatures", return_value={"coretemp": [psutil_entry]}, create=True
        ):
            result = self._collector(_LHM_TREE).collect()
        self.assertEqual(result["sensors"][0]["chip"], "coretemp")
        self.assertEqual(len(result["sensors"]), 1)


if __name__ == "__main__":
    unittest.main()

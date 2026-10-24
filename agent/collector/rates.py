"""Counter delta calculation for cumulative operating-system counters."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Mapping


@dataclass(frozen=True)
class ByteCounters:
    """The receive/read and send/write totals observed at one instant."""

    inbound_bytes: int
    outbound_bytes: int


@dataclass(frozen=True)
class ByteRates:
    """Rates derived from two cumulative counter observations."""

    inbound_Bps: float | None
    outbound_Bps: float | None


class ByteRateTracker:
    """Maintain an independent baseline per counter key.

    A first observation, non-positive elapsed time, or a counter reset deliberately
    produces ``None`` rates. This avoids presenting a fabricated speed.
    """

    def __init__(self) -> None:
        self._previous: dict[str, tuple[ByteCounters, float]] = {}

    def sample(
        self,
        current: Mapping[str, ByteCounters],
        timestamp: float | None = None,
    ) -> dict[str, ByteRates]:
        observed_at = monotonic() if timestamp is None else timestamp
        rates: dict[str, ByteRates] = {}

        for key, counters in current.items():
            previous = self._previous.get(key)
            inbound_rate: float | None = None
            outbound_rate: float | None = None
            if previous is not None:
                previous_counters, previous_at = previous
                elapsed_seconds = observed_at - previous_at
                inbound_delta = counters.inbound_bytes - previous_counters.inbound_bytes
                outbound_delta = counters.outbound_bytes - previous_counters.outbound_bytes
                if elapsed_seconds > 0 and inbound_delta >= 0 and outbound_delta >= 0:
                    inbound_rate = inbound_delta / elapsed_seconds
                    outbound_rate = outbound_delta / elapsed_seconds

            rates[key] = ByteRates(inbound_rate, outbound_rate)
            self._previous[key] = (counters, observed_at)

        return rates

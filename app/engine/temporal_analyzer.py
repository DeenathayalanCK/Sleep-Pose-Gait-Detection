import time
import logging

logger = logging.getLogger(__name__)


class TemporalAnalyzer:
    """
    Smooth noisy per-frame detections over a sliding time window.

    BUG FIX: temporal_analyzer.py was completely empty — any code that
    imported TemporalAnalyzer would get an ImportError.  This class now
    provides proper temporal smoothing so a single blinking frame doesn't
    toggle the fatigue state.
    """

    def __init__(self, window_seconds: float = 2.0, threshold: float = 0.6):
        self.window   = window_seconds
        self.threshold = threshold
        self._events: list[tuple[float, bool]] = []

    def update(self, value: bool) -> bool:
        now = self._now()
        self._events.append((now, value))
        # Drop events outside the window
        self._events = [(t, v) for t, v in self._events if now - t <= self.window]

        if not self._events:
            return False

        ratio = sum(v for _, v in self._events) / len(self._events)
        return ratio >= self.threshold

    @staticmethod
    def _now() -> float:
        return time.monotonic()

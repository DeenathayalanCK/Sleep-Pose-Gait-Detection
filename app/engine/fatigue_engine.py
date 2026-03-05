import time
import logging
from app.detection.sleep_pose_detector import SleepAnalysis

logger = logging.getLogger(__name__)


class FatigueEngine:
    """
    Tracks how long the person has been in 'sleeping' state continuously.
    Fires an alert when they cross the threshold.

    Also debounces alerts — once fired, waits COOLDOWN_SECONDS before
    firing again for the same sleep episode.
    """
    COOLDOWN_SECONDS = 30.0   # don't spam alerts for the same sleep episode

    def __init__(self):
        self._sleep_start:   float | None = None
        self._last_alert_at: float | None = None

    def update(self, analysis: SleepAnalysis) -> tuple[bool, float]:
        """
        Returns (should_alert, sleep_duration_seconds).
        should_alert is True only on the leading edge of a threshold crossing,
        and respects the cooldown.
        """
        now = time.monotonic()

        if analysis.state == "sleeping":
            if self._sleep_start is None:
                self._sleep_start = now
                logger.debug("Sleep episode started")

            duration = now - self._sleep_start

            # Check cooldown to avoid duplicate alerts
            in_cooldown = (
                self._last_alert_at is not None
                and (now - self._last_alert_at) < self.COOLDOWN_SECONDS
            )

            if not in_cooldown:
                self._last_alert_at = now
                return True, round(duration, 1)

        else:
            if self._sleep_start is not None:
                logger.info(f"Sleep episode ended after {now - self._sleep_start:.1f}s")
            self._sleep_start = None

        return False, 0.0
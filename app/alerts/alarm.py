import logging

logger = logging.getLogger(__name__)


def trigger_alarm(state: str, duration: float) -> None:
    """
    BUG FIX: alarm.py was empty — calling trigger_alarm() anywhere would
    raise AttributeError.  This stub logs the alarm and is the extension
    point for audio/visual alerts.
    """
    logger.warning(f"[ALARM] State={state} | Duration={duration:.1f}s")

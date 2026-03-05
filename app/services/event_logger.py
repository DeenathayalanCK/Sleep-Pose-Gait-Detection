import logging
logger = logging.getLogger(__name__)

def log_event(**kwargs):
    """
    Legacy stub — event logging now handled by FatigueEngine via repository.py.
    Accepts any kwargs silently so old callers don't crash.
    """
    logger.debug(f"log_event() called (stub) with: {list(kwargs.keys())}")
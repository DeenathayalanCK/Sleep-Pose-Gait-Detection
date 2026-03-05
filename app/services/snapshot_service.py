import cv2
import os
import time
import logging
from app.config import SNAPSHOT_DIR

logger = logging.getLogger(__name__)

# Always use absolute path — eliminates CWD ambiguity inside Docker
_ABS_SNAPSHOT_DIR = os.path.abspath(SNAPSHOT_DIR)


def save_snapshot(frame) -> str | None:
    """Save annotated frame as JPEG. Returns absolute path or None on failure."""
    try:
        os.makedirs(_ABS_SNAPSHOT_DIR, exist_ok=True)
        path = os.path.join(_ABS_SNAPSHOT_DIR, f"snap_{int(time.time() * 1000)}.jpg")
        ok = cv2.imwrite(path, frame)
        if not ok:
            logger.error(f"cv2.imwrite failed for {path} — frame shape={getattr(frame, 'shape', 'N/A')}")
            return None
        logger.debug(f"Snapshot saved: {path}")
        return path
    except Exception as e:
        logger.error(f"save_snapshot exception: {e}")
        return None
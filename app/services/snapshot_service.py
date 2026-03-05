import cv2
import os
import time
import logging
import numpy as np
from app.config import SNAPSHOT_DIR

logger = logging.getLogger(__name__)

_ABS_SNAPSHOT_DIR = os.path.abspath(SNAPSHOT_DIR)


def _write(path: str, frame: np.ndarray) -> str | None:
    """Write frame to disk. Returns path on success, None on failure."""
    try:
        os.makedirs(_ABS_SNAPSHOT_DIR, exist_ok=True)
        ok = cv2.imwrite(path, frame)
        if not ok:
            logger.error(f"cv2.imwrite failed: {path} shape={getattr(frame,'shape','?')}")
            return None
        logger.debug(f"Saved: {path}")
        return path
    except Exception as e:
        logger.error(f"save error: {e}")
        return None


def save_snapshot(frame: np.ndarray) -> str | None:
    """Save full annotated frame. Returns absolute path or None."""
    ts   = int(time.time() * 1000)
    path = os.path.join(_ABS_SNAPSHOT_DIR, f"snap_{ts}.jpg")
    return _write(path, frame)


def save_person_crop(frame: np.ndarray,
                     x1: int, y1: int, x2: int, y2: int,
                     track_id: int,
                     pad: int = 30) -> str | None:
    """
    Crop the person region from frame, add padding, resize to a fixed
    portrait thumbnail (160×220), and save as a separate JPEG.

    Returns absolute path or None on failure.
    Saved as: crop_<track_id>_<timestamp_ms>.jpg
    """
    try:
        h, w = frame.shape[:2]
        cx1  = max(0, x1 - pad)
        cy1  = max(0, y1 - pad)
        cx2  = min(w, x2 + pad)
        cy2  = min(h, y2 + pad)

        crop = frame[cy1:cy2, cx1:cx2]
        if crop.size == 0:
            logger.warning(f"Empty crop for P{track_id} bbox=({x1},{y1},{x2},{y2})")
            return None

        # Resize to fixed portrait thumbnail — consistent size for UI display
        thumb = cv2.resize(crop, (160, 220), interpolation=cv2.INTER_AREA)

        ts   = int(time.time() * 1000)
        path = os.path.join(_ABS_SNAPSHOT_DIR, f"crop_{track_id}_{ts}.jpg")
        return _write(path, thumb)

    except Exception as e:
        logger.error(f"save_person_crop error: {e}")
        return None
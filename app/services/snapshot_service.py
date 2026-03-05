import cv2
import os
import time
import logging
from app.config import SNAPSHOT_DIR

logger = logging.getLogger(__name__)


def save_snapshot(frame):
    # BUG FIX: original never created the directory — cv2.imwrite silently
    # fails and returns False, leaving snapshot=None stored in the DB.
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    path = f"{SNAPSHOT_DIR}/snap_{int(time.time())}.jpg"
    success = cv2.imwrite(path, frame)

    if not success:
        logger.error(f"Failed to write snapshot to {path}")
        return None

    return path

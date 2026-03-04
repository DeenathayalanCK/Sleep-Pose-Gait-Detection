import cv2
import time
from app.config import SNAPSHOT_DIR

def save_snapshot(frame):

    path = f"{SNAPSHOT_DIR}/snap_{int(time.time())}.jpg"

    cv2.imwrite(path, frame)

    return path
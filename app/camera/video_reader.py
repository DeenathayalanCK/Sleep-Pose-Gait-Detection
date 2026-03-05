import cv2
import logging
from app.config import VIDEO_SOURCE, FRAME_WIDTH, FRAME_HEIGHT

logger = logging.getLogger(__name__)


class VideoReader:

    def __init__(self, source=None):
        self.source = source or VIDEO_SOURCE
        self.cap = None
        self._open()

    def _open(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            logger.error(f"Cannot open video source: {self.source}")

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            self._open()
            return None

        ret, frame = self.cap.read()
        if not ret:
            # For recorded video: rewind to loop, or return None to signal EOF
            logger.warning("End of video or read failure — rewinding.")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return None

        return frame

    def release(self):
        if self.cap:
            self.cap.release()
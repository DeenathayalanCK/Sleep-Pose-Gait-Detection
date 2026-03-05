import cv2
import threading
import logging
from app.camera.frame_buffer import FrameBuffer

logger = logging.getLogger(__name__)


class RTSPStream:
    """
    Reads an RTSP stream on a background thread and exposes the latest frame
    via a FrameBuffer.

    BUG FIX: rtsp_stream.py was completely empty.  This is the correct
    pattern for RTSP — blocking cap.read() in the main thread causes the
    processing pipeline to stall on network latency.
    """

    def __init__(self, url: str):
        self.url    = url
        self.buffer = FrameBuffer()
        self._stop  = threading.Event()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)

    def start(self):
        self._thread.start()
        logger.info(f"RTSP stream started: {self.url}")

    def stop(self):
        self._stop.set()

    def read(self):
        return self.buffer.get()

    def _read_loop(self):
        cap = cv2.VideoCapture(self.url)
        if not cap.isOpened():
            logger.error(f"Cannot open RTSP stream: {self.url}")
            return

        while not self._stop.is_set():
            ret, frame = cap.read()
            if ret:
                self.buffer.put(frame)

        cap.release()

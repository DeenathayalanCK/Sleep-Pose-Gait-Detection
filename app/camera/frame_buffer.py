import threading
import logging

logger = logging.getLogger(__name__)


class FrameBuffer:
    """
    Thread-safe single-slot frame buffer.

    BUG FIX: frame_buffer.py was completely empty.  Without a frame buffer,
    the RTSP reader and the processing thread share no safe handoff — leading
    to race conditions and dropped/stale frames.
    """

    def __init__(self):
        self._frame = None
        self._lock  = threading.Lock()

    def put(self, frame):
        with self._lock:
            self._frame = frame

    def get(self):
        with self._lock:
            return self._frame

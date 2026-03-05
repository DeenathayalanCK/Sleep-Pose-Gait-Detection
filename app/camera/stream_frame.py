import threading
import numpy as np
from typing import Optional

class StreamFrame:
    """
    Thread-safe single slot that holds the latest annotated frame as JPEG bytes.
    The monitor thread writes to it; the /stream endpoint reads from it.
    """
    def __init__(self):
        self._lock  = threading.Lock()
        self._frame: Optional[bytes] = None

    def write(self, jpeg_bytes: bytes):
        with self._lock:
            self._frame = jpeg_bytes

    def read(self) -> Optional[bytes]:
        with self._lock:
            return self._frame

# Singleton — imported by both main.py and routes.py
latest_frame = StreamFrame()
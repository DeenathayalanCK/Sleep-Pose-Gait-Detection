import threading
from typing import Optional


class StreamFrame:
    """
    Thread-safe single-slot frame store with a monotonic counter.

    The counter increments on every write. The stream generator compares
    counter values (not object identity) to detect new frames reliably.
    This avoids the 'is not' identity check which breaks when the monitor
    thread writes multiple frames between generator wake-ups.
    """
    def __init__(self):
        self._lock    = threading.Lock()
        self._frame:  Optional[bytes] = None
        self._counter: int = 0          # increments on every new frame

    def write(self, jpeg_bytes: bytes):
        with self._lock:
            self._frame   = jpeg_bytes
            self._counter += 1

    def read(self) -> tuple[Optional[bytes], int]:
        """Returns (jpeg_bytes, counter). Counter lets callers detect new frames."""
        with self._lock:
            return self._frame, self._counter


# Singleton
latest_frame = StreamFrame()
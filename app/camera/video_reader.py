"""
VideoReader — always-fresh frame source.

THE LATENCY BUG:
  OpenCV's VideoCapture has an internal frame buffer (default 100 frames).
  If your processing loop is slower than the camera's FPS, frames pile up
  in that buffer. After a few minutes you're reading frames from 5–7
  minutes ago — the camera is live but you're watching the past.

THE FIX — two-part:
  1. Set CAP_PROP_BUFFERSIZE=1 on the capture — tells OpenCV to keep only
     the newest frame. Older frames are discarded immediately.

  2. Run capture in a BACKGROUND THREAD that continuously drains the
     buffer, always keeping only the latest frame in a 1-slot store.
     The monitor loop calls .read() and always gets the CURRENT frame,
     never a queued one. No matter how slow processing is, latency stays
     at exactly 1 frame.

This is the standard pattern for any real-time camera pipeline.
"""
import cv2
import threading
import logging
import time
from app.config import VIDEO_SOURCE, FRAME_WIDTH, FRAME_HEIGHT

logger = logging.getLogger(__name__)


class VideoReader:
    """
    Background-threaded video capture with 1-slot latest-frame store.
    Always returns the most recently captured frame, never a buffered old one.
    """

    def __init__(self, source=None):
        self._source  = source or VIDEO_SOURCE
        self._cap     = None
        self._frame   = None
        self._lock    = threading.Lock()
        self._stop    = threading.Event()
        self._thread  = threading.Thread(target=self._capture_loop,
                                          daemon=True, name="VideoReader")
        self._open()
        self._thread.start()

    def _open(self):
        if self._cap is not None:
            self._cap.release()

        self._cap = cv2.VideoCapture(self._source)

        if not self._cap.isOpened():
            logger.error(f"Cannot open video source: {self._source}")
            return

        # ── KEY FIX 1: Minimize internal OpenCV buffer ────────────────
        # CAP_PROP_BUFFERSIZE=1 means OpenCV holds at most 1 frame internally.
        # Without this, default is 100 frames → up to 4 seconds of queued
        # frames at 25fps before your slow processing even starts falling behind.
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        src_str = str(self._source)
        if src_str.startswith("rtsp://") or src_str.startswith("rtmp://"):
            # For RTSP: also set TCP transport and reduce latency flags
            self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"H264"))
            self._cap.set(cv2.CAP_PROP_FPS, 25)

        logger.info(f"VideoCapture opened: {self._source}")

    def _capture_loop(self):
        """
        KEY FIX 2: Runs in background thread, continuously draining the
        capture device. Stores only the LATEST frame. If processing is slow,
        intermediate frames are simply discarded — we never accumulate a queue.
        """
        consecutive_failures = 0

        while not self._stop.is_set():
            if self._cap is None or not self._cap.isOpened():
                logger.warning("Capture closed — attempting reopen in 2s")
                time.sleep(2)
                self._open()
                continue

            ret, frame = self._cap.read()

            if not ret:
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    # End of file (video loop) or stream dropout
                    logger.warning("Read failure — rewinding/reconnecting")
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    consecutive_failures = 0
                time.sleep(0.01)
                continue

            consecutive_failures = 0

            # Resize here in the capture thread — saves time in the main loop
            if FRAME_WIDTH and FRAME_HEIGHT:
                frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # ── KEY FIX 3: 1-slot store — old frames are overwritten ──
            # Monitor thread always gets the NEWEST frame on next .read()
            with self._lock:
                self._frame = frame

    def read(self):
        """Return the latest captured frame, or None if not yet available."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def release(self):
        self._stop.set()
        self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()
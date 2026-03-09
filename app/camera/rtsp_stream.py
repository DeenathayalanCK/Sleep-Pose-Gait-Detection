"""
RTSPStream — same 1-slot architecture as VideoReader.
Kept separate because RTSP needs reconnect logic on dropout.
"""
import cv2
import threading
import logging
import time

logger = logging.getLogger(__name__)


class RTSPStream:
    def __init__(self, url: str,
                 width: int = 640, height: int = 480):
        self._url    = url
        self._width  = width
        self._height = height
        self._frame  = None
        self._lock   = threading.Lock()
        self._stop   = threading.Event()
        self._thread = threading.Thread(
            target=self._read_loop, daemon=True, name="RTSPStream"
        )
        self._thread.start()

    def read(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def stop(self):
        self._stop.set()

    def _read_loop(self):
        while not self._stop.is_set():
            cap = cv2.VideoCapture(self._url)
            if not cap.isOpened():
                logger.error(f"Cannot open RTSP: {self._url} — retry in 5s")
                time.sleep(5)
                continue

            # 1-frame buffer — critical for RTSP latency
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            logger.info(f"RTSP connected: {self._url}")

            while not self._stop.is_set():
                ret, frame = cap.read()
                if not ret:
                    logger.warning("RTSP read failed — reconnecting")
                    break
                if self._width and self._height:
                    frame = cv2.resize(frame, (self._width, self._height))
                with self._lock:
                    self._frame = frame  # always latest, old frame discarded

            cap.release()
            if not self._stop.is_set():
                logger.info("RTSP reconnecting in 2s…")
                time.sleep(2)
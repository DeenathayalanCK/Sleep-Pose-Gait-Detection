import os
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

import cv2
import time
import logging
import datetime
from contextlib import asynccontextmanager
from threading import Thread

from app.utils.logger import setup_logger
from app.database.db import init_db
from app.api.server import create_app
from app.config import FRAME_WIDTH, FRAME_HEIGHT, CAMERA_ID

from app.camera.video_reader import VideoReader
from app.camera.stream_frame import latest_frame
from app.tracking.person_tracker import PersonTracker
from app.tracking.track_manager import TrackManager
from app.utils.annotator import draw_person, draw_global_overlay

setup_logger()
logger = logging.getLogger(__name__)

# Global status — list of per-person dicts for /status endpoint
current_persons: dict = {}   # track_id → status dict


def monitor():
    logger.info("Multi-person monitoring started.")

    video        = VideoReader()
    tracker      = PersonTracker()
    track_mgr    = TrackManager()

    frame_time   = time.monotonic()

    while True:
        try:
            frame = video.read()
            if frame is None:
                time.sleep(0.03)
                continue

            now = time.monotonic()
            dt  = now - frame_time
            frame_time = now

            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # ── Detect + track all persons ────────────────────────────────
            persons = tracker.update(frame)

            # ── Per-person pose + state + event management ────────────────
            annotated = frame.copy()

            # First pass: draw global header
            # (person_states not yet populated — draw after second pass)

            # Build partial annotated with per-person drawings
            person_states = track_mgr.update(
                persons, frame, annotated_frame=annotated
            )

            # Draw per-person boxes + skeletons + labels
            # We need bbox from the tracker result — build a lookup
            bbox_by_id = {p.track_id: p for p in persons}
            for tid, ps in person_states.items():
                p = bbox_by_id.get(tid)
                if p:
                    draw_person(
                        annotated,
                        track_id=tid,
                        x1=p.x1, y1=p.y1, x2=p.x2, y2=p.y2,
                        state=ps.state,
                        analysis=ps.analysis,
                        pose_landmarks=ps.analysis.pose_landmarks,
                    )

            # Draw global header bar
            draw_global_overlay(annotated, person_states, CAMERA_ID)

            # ── Update global status dict ─────────────────────────────────
            current_persons.clear()
            for tid, ps in person_states.items():
                current_persons[str(tid)] = {
                    "track_id":        tid,
                    "state":           ps.state,
                    "confidence":      ps.analysis.confidence,
                    "inactive_seconds":ps.analysis.inactive_seconds,
                    "reclined_ratio":  ps.analysis.reclined_ratio,
                    "motion_score":    ps.analysis.motion_score,
                    "pose_visible":    ps.analysis.pose_visible,
                    "updated_at":      datetime.datetime.now().isoformat(),
                }

            # ── Push annotated frame to MJPEG stream ──────────────────────
            _, jpeg = cv2.imencode(".jpg", annotated,
                                   [cv2.IMWRITE_JPEG_QUALITY, 72])
            latest_frame.write(jpeg.tobytes())

        except Exception as e:
            logger.error(f"Monitoring error: {e}", exc_info=True)
            time.sleep(1)


@asynccontextmanager
async def lifespan(app_instance):
    init_db()
    Thread(target=monitor, daemon=True).start()
    logger.info("Monitoring thread started.")
    yield
    logger.info("Shutdown complete.")


app = create_app()
app.router.lifespan_context = lifespan
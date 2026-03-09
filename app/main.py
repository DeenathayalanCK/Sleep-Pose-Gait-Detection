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

current_persons: dict = {}


def monitor():
    logger.info("Multi-person monitoring started.")

    video      = VideoReader()          # now runs its own background capture thread
    tracker    = PersonTracker()
    track_mgr  = TrackManager()

    # ── FPS tracking for diagnostics ─────────────────────────────────
    fps_counter = 0
    fps_timer   = time.monotonic()
    processing_fps = 0.0

    # ── KEY FIX: frame deduplication ─────────────────────────────────
    # Don't process the same frame twice. If VideoReader hasn't produced
    # a new frame yet (processing is faster than capture), skip and wait.
    last_frame_id = id(None)

    while True:
        try:
            frame = video.read()

            # No frame available yet — yield CPU, don't spin
            if frame is None:
                time.sleep(0.005)
                continue

            # Skip if this is the exact same frame object as last iteration
            # (processing loop ran faster than capture thread)
            fid = id(frame)
            if fid == last_frame_id:
                time.sleep(0.005)
                continue
            last_frame_id = fid

            # ── Detect + track ────────────────────────────────────────
            persons = tracker.update(frame)

            # ── Per-person pose analysis ──────────────────────────────
            annotated = frame.copy()

            person_states = track_mgr.update(
                persons, frame, annotated_frame=annotated
            )

            # ── Draw annotations ──────────────────────────────────────
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

            # ── FPS overlay ───────────────────────────────────────────
            fps_counter += 1
            elapsed = time.monotonic() - fps_timer
            if elapsed >= 2.0:
                processing_fps = fps_counter / elapsed
                fps_counter    = 0
                fps_timer      = time.monotonic()

            draw_global_overlay(annotated, person_states, CAMERA_ID)

            # Burn processing FPS into frame so you can monitor it live
            cv2.putText(
                annotated,
                f"{processing_fps:.1f} fps",
                (FRAME_WIDTH - 80, FRAME_HEIGHT - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                (80, 80, 80), 1, cv2.LINE_AA,
            )

            # ── Update /status ────────────────────────────────────────
            current_persons.clear()
            for tid, ps in person_states.items():
                current_persons[str(tid)] = {
                    "track_id":         tid,
                    "state":            ps.state,
                    "confidence":       ps.analysis.confidence,
                    "inactive_seconds": ps.analysis.inactive_seconds,
                    "reclined_ratio":   ps.analysis.reclined_ratio,
                    "motion_score":     ps.analysis.motion_score,
                    "pose_visible":     ps.analysis.pose_visible,
                    "signals":          ps.analysis.signals,
                    "updated_at":       datetime.datetime.now().isoformat(),
                }

            # ── Push to MJPEG stream ──────────────────────────────────
            # JPEG quality 75 — good balance of quality vs bandwidth.
            # Lower this to 60 if stream is choppy on slow networks.
            _, jpeg = cv2.imencode(
                ".jpg", annotated,
                [cv2.IMWRITE_JPEG_QUALITY, 75]
            )
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
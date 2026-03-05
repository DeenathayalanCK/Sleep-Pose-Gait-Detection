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

from app.camera.video_reader import VideoReader
from app.camera.stream_frame import latest_frame
from app.detection.sleep_pose_detector import SleepPoseDetector
from app.detection.face_mesh import FaceMeshDetector
from app.detection.eye_landmarks import extract_eye_landmarks
from app.detection.fatigue_detector import FatigueDetector
from app.engine.fatigue_engine import FatigueEngine
from app.engine.state_analyzer import StateAnalyzer
from app.utils.annotator import draw_overlay
from app.services.snapshot_service import save_snapshot
from app.services.event_logger import log_event
from app.llm.event_summarizer import summarize

setup_logger()
logger = logging.getLogger(__name__)

# ── Shared live state (written by monitor thread, read by /status) ────────────
current_status: dict = {
    "state":            "starting",
    "confidence":       0.0,
    "inactive_seconds": 0.0,
    "reclined_ratio":   0.0,
    "motion_score":     0.0,
    "pose_visible":     False,
    "ear":              None,
    "updated_at":       None,
}


# ── Monitor loop ──────────────────────────────────────────────────────────────
def monitor():
    logger.info("Fatigue monitoring started.")

    video          = VideoReader()
    sleep_detector = SleepPoseDetector()
    mesh           = FaceMeshDetector()
    eye_detector   = FatigueDetector()
    engine         = FatigueEngine()
    state_analyzer = StateAnalyzer()

    while True:
        try:
            frame = video.read()
            if frame is None:
                time.sleep(0.03)
                continue

            frame = cv2.resize(frame, (640, 480))

            # ── Primary: pose-based sleep detection ───────────────────────
            analysis = sleep_detector.process(frame)

            # ── Secondary: EAR eye detection (frontal face only) ─────────
            ear = None
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face = mesh.detect(rgb)
            if face is not None:
                h, w, _ = frame.shape
                left_eye, right_eye = extract_eye_landmarks(face, w, h)
                eye_closed, ear = eye_detector.check(left_eye, right_eye)
                if eye_closed and analysis.state != "sleeping":
                    analysis.state = "drowsy"

            # ── Final state ───────────────────────────────────────────────
            inactive = analysis.inactive_seconds > 20
            state    = state_analyzer.analyze(analysis.state, inactive)

            # ── Update shared status ──────────────────────────────────────
            current_status.update({
                "state":            state,
                "confidence":       analysis.confidence,
                "inactive_seconds": analysis.inactive_seconds,
                "reclined_ratio":   analysis.reclined_ratio,
                "motion_score":     analysis.motion_score,
                "pose_visible":     analysis.pose_visible,
                "ear":              round(ear, 3) if ear else None,
                "updated_at":       datetime.datetime.now().isoformat(),
            })

            # ── Annotate frame and push to stream ─────────────────────────
            annotated = draw_overlay(frame, analysis, state, ear)
            _, jpeg = cv2.imencode(
                ".jpg", annotated,
                [cv2.IMWRITE_JPEG_QUALITY, 70]
            )
            latest_frame.write(jpeg.tobytes())

            # ── Alert ─────────────────────────────────────────────────────
            should_alert, duration = engine.update(analysis)
            if should_alert:
                logger.warning(
                    f"SLEEP DETECTED | {duration}s "
                    f"recline={analysis.reclined_ratio:.2f} "
                    f"inactive={analysis.inactive_seconds:.0f}s"
                )
                snapshot = save_snapshot(annotated)   # save annotated frame
                summary  = summarize(duration)
                log_event(duration=duration, snapshot=snapshot,
                          summary=summary, state=state)

        except Exception as e:
            logger.error(f"Monitoring error: {e}", exc_info=True)
            time.sleep(1)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app_instance):
    init_db()
    Thread(target=monitor, daemon=True).start()
    logger.info("Monitoring thread started.")
    yield
    logger.info("Shutdown complete.")


app = create_app()
app.router.lifespan_context = lifespan
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
from app.config import FRAME_WIDTH, FRAME_HEIGHT, SLEEP_SECONDS

from app.camera.video_reader import VideoReader
from app.camera.stream_frame import latest_frame
from app.detection.sleep_pose_detector import SleepPoseDetector
from app.detection.face_mesh import FaceMeshDetector
from app.detection.eye_landmarks import extract_eye_landmarks
from app.detection.fatigue_detector import FatigueDetector
from app.engine.fatigue_engine import FatigueEngine
from app.engine.state_analyzer import StateAnalyzer
from app.utils.annotator import draw_overlay

setup_logger()
logger = logging.getLogger(__name__)

current_status: dict = {
    "state":            "starting",
    "confidence":       0.0,
    "inactive_seconds": 0.0,
    "reclined_ratio":   0.0,
    "motion_score":     0.0,
    "pose_visible":     False,
    "posture":          "unknown",
    "ear":              None,
    "updated_at":       None,
}


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

            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            fh, fw = frame.shape[:2]

            # Primary: pose-based detection — landmarks carried in analysis
            analysis = sleep_detector.process(frame)

            # Secondary: EAR when frontal face visible
            ear  = None
            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face = mesh.detect(rgb)
            if face is not None:
                left_eye, right_eye = extract_eye_landmarks(face, fw, fh)
                eye_closed, ear = eye_detector.check(left_eye, right_eye)
                if eye_closed and analysis.state != "sleeping":
                    analysis.state = "drowsy"

            inactive = analysis.inactive_seconds > SLEEP_SECONDS
            # Pass landmarks + motion to state_analyzer for posture classification
            state = state_analyzer.analyze(
                pose_state    = analysis.state,
                inactive      = inactive,
                pose_landmarks= analysis.pose_landmarks,
                frame_h       = fh,
                frame_w       = fw,
                motion_score  = analysis.motion_score,
            )

            current_status.update({
                "state":            state,
                "confidence":       analysis.confidence,
                "inactive_seconds": analysis.inactive_seconds,
                "reclined_ratio":   analysis.reclined_ratio,
                "motion_score":     analysis.motion_score,
                "pose_visible":     analysis.pose_visible,
                "posture":          state,
                "ear":              round(ear, 3) if ear else None,
                "updated_at":       datetime.datetime.now().isoformat(),
            })

            # Annotate frame with skeleton, bounding box, state banner
            annotated = draw_overlay(
                frame, analysis, state, ear, analysis.pose_landmarks
            )
            _, jpeg = cv2.imencode(".jpg", annotated,
                                   [cv2.IMWRITE_JPEG_QUALITY, 72])
            latest_frame.write(jpeg.tobytes())

            # Save event + snapshot — all handled inside engine (non-blocking)
            engine.update(analysis, snapshot_frame=annotated)

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
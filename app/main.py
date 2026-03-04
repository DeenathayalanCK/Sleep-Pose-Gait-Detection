import cv2
import time
import logging
from fastapi import FastAPI
from threading import Thread

from app.camera.video_reader import VideoReader
from app.detection.face_mesh import FaceMeshDetector
from app.detection.eye_landmarks import extract_eye_landmarks
from app.detection.fatigue_detector import FatigueDetector
from app.engine.fatigue_engine import FatigueEngine
from app.services.snapshot_service import save_snapshot
from app.services.event_logger import log_event
from app.llm.event_summarizer import summarize


# -------------------------------------------------
# Logging
# -------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# -------------------------------------------------
# FastAPI App
# -------------------------------------------------

app = FastAPI(title="Fatigue Detection AI")


# -------------------------------------------------
# Initialize Modules
# -------------------------------------------------

video = VideoReader()

mesh = FaceMeshDetector()

detector = FatigueDetector()

engine = FatigueEngine()


# -------------------------------------------------
# Monitoring Loop
# -------------------------------------------------

def monitor():

    logger.info("Fatigue monitoring started")

    while True:

        try:

            frame = video.read()

            if frame is None:
                time.sleep(0.01)
                continue

            frame = cv2.resize(frame, (640, 480))

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            face = mesh.detect(rgb)

            if face is None:
                continue

            h, w, _ = frame.shape

            left_eye, right_eye = extract_eye_landmarks(face, w, h)

            closed, ear = detector.check(left_eye, right_eye)

            fatigue, duration = engine.update(closed)

            if fatigue:

                logger.info(f"Fatigue detected: {duration:.2f} sec")

                snapshot = save_snapshot(frame)

                summary = summarize(duration)

                log_event(
                    duration=duration,
                    snapshot=snapshot,
                    summary=summary
                )

            # Small delay to reduce CPU load
            time.sleep(0.01)

        except Exception as e:

            logger.error(f"Monitoring error: {e}")

            time.sleep(1)


# -------------------------------------------------
# Start Monitoring Thread
# -------------------------------------------------

@app.on_event("startup")
def start_monitor():

    thread = Thread(target=monitor)

    thread.daemon = True

    thread.start()

    logger.info("Monitoring thread started")


# -------------------------------------------------
# Health Check API
# -------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "running",
        "service": "fatigue-detection-ai"
    }
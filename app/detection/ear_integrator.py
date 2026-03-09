"""
ear_integrator.py — EAR (Eye Aspect Ratio) + PERCLOS integration.

PERCLOS = Percentage of Eye Closure over a time window.
          Clinical gold standard for drowsiness detection.
          Threshold: >15% eye closure in 60 frames = drowsy onset.
                     >40% eye closure in 60 frames = high fatigue.

How it works:
  - FaceMesh runs on the person CROP (same crop MediaPipe pose uses).
  - EAR is computed each frame from 6 eye landmark points per eye.
  - A 60-frame rolling buffer tracks the fraction of frames where
    both eyes were below EAR_THRESHOLD.
  - PERCLOS drives an independent drowsy/sleep signal that feeds
    directly into the multi-signal fusion in SleepPoseDetector.

Why this is better than pose alone:
  - EAR is a direct physiological signal — eye closure IS drowsiness.
  - Works even when body posture looks normal (person sitting upright
    but eyes drooping — the hardest case for pose-only detection).
  - Completely independent signal pathway — no shared assumptions
    with spine/head/recline signals.
"""
import os
import logging
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)

# PERCLOS thresholds
_PERCLOS_DROWSY = float(os.getenv("PERCLOS_DROWSY_THRESHOLD", "0.15"))  # 15% closure
_PERCLOS_SLEEP  = float(os.getenv("PERCLOS_SLEEP_THRESHOLD",  "0.40"))  # 40% closure
_PERCLOS_WINDOW = int(os.getenv("PERCLOS_WINDOW_FRAMES",      "60"))    # rolling window

# MediaPipe FaceMesh eye landmark indices
_LEFT_EYE  = [33, 160, 158, 133, 153, 144]
_RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Minimum face detection confidence to trust EAR reading
_FACE_CONF_MIN = float(os.getenv("EAR_FACE_CONF_MIN", "0.50"))


def _dist(p1, p2) -> float:
    return float(np.linalg.norm(np.array(p1) - np.array(p2)))


def _compute_ear(eye_pts: list) -> float:
    """
    Eye Aspect Ratio = (||p1-p5|| + ||p2-p4||) / (2 * ||p0-p3||)
    Vertical distances / horizontal distance.
    Open eye ~0.30. Closing eye <0.25. Fully closed <0.15.
    """
    A = _dist(eye_pts[1], eye_pts[5])
    B = _dist(eye_pts[2], eye_pts[4])
    C = _dist(eye_pts[0], eye_pts[3])
    return (A + B) / (2.0 * C + 1e-6)


def _extract_eye_pts(face_lms, w: int, h: int):
    """Extract pixel coords of 6 landmarks per eye from FaceMesh result."""
    left  = [(int(face_lms.landmark[i].x * w),
              int(face_lms.landmark[i].y * h)) for i in _LEFT_EYE]
    right = [(int(face_lms.landmark[i].x * w),
              int(face_lms.landmark[i].y * h)) for i in _RIGHT_EYE]
    return left, right


class EARIntegrator:
    """
    Per-person EAR tracker with PERCLOS computation.
    One instance per tracked person, lives inside PersonState.

    Usage:
        integrator = EARIntegrator()
        result = integrator.process(bgr_crop)
        # result.perclos, result.ear, result.drowsy_by_ear, result.sleep_by_ear
    """

    def __init__(self):
        import os
        os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")
        import mediapipe as mp

        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=_FACE_CONF_MIN,
            min_tracking_confidence=0.5,
        )
        # Rolling buffer: True = eye closed this frame, False = open
        self._closure_buf: deque = deque(maxlen=_PERCLOS_WINDOW)
        self._no_face_frames: int = 0
        self._last_ear: float = 0.30   # default open

    def process(self, bgr_crop: np.ndarray) -> "EARResult":
        """
        Run FaceMesh on crop, compute EAR + PERCLOS.
        Returns EARResult with all signals.
        """
        import cv2
        h, w = bgr_crop.shape[:2]

        # Skip tiny crops — face won't be visible
        if h < 40 or w < 30:
            return EARResult(face_found=False)

        rgb    = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(rgb)

        if result.multi_face_landmarks is None:
            self._no_face_frames += 1
            # If face absent for >30 frames, clear buffer (person left)
            if self._no_face_frames > 30:
                self._closure_buf.clear()
            return EARResult(face_found=False)

        self._no_face_frames = 0
        face_lms = result.multi_face_landmarks[0]

        left_pts, right_pts = _extract_eye_pts(face_lms, w, h)
        left_ear  = _compute_ear(left_pts)
        right_ear = _compute_ear(right_pts)
        ear       = (left_ear + right_ear) / 2.0
        self._last_ear = ear

        threshold = float(os.getenv("EAR_THRESHOLD", "0.25"))
        eyes_closed = ear < threshold
        self._closure_buf.append(eyes_closed)

        # PERCLOS = fraction of window where eyes were closed
        perclos = (sum(self._closure_buf) / len(self._closure_buf)
                   if self._closure_buf else 0.0)

        return EARResult(
            face_found    = True,
            ear           = round(ear, 3),
            left_ear      = round(left_ear, 3),
            right_ear     = round(right_ear, 3),
            eyes_closed   = eyes_closed,
            perclos       = round(perclos, 3),
            drowsy_by_ear = perclos >= _PERCLOS_DROWSY,
            sleep_by_ear  = perclos >= _PERCLOS_SLEEP,
            window_size   = len(self._closure_buf),
        )

    def close(self):
        self._face_mesh.close()


import os  # needed for os.getenv inside process()

from dataclasses import dataclass, field


@dataclass
class EARResult:
    face_found:    bool  = False
    ear:           float = 0.0
    left_ear:      float = 0.0
    right_ear:     float = 0.0
    eyes_closed:   bool  = False
    perclos:       float = 0.0
    drowsy_by_ear: bool  = False
    sleep_by_ear:  bool  = False
    window_size:   int   = 0
import os
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

import time
import logging
import numpy as np
import mediapipe as mp
from dataclasses import dataclass, field
from typing import Optional

from app.config import (
    MOTION_THRESHOLD, SLEEP_SECONDS, DROWSY_SECONDS,
    SLEEP_SECONDS_RECLINED, RECLINE_THRESHOLD, RECLINE_MIN,
    POSE_DETECTION_CONFIDENCE, POSE_TRACKING_CONFIDENCE,
    POSE_LANDMARK_MIN_VISIBILITY, RECLINE_SMOOTH_FRAMES,
)

logger = logging.getLogger(__name__)

_NOSE=0; _L_SHOULDER=11; _R_SHOULDER=12
_L_HIP=23; _R_HIP=24; _L_KNEE=25; _R_KNEE=26
_L_ANKLE=27; _R_ANKLE=28; _L_WRIST=15; _R_WRIST=16


@dataclass
class SleepAnalysis:
    state: str = "unknown"
    confidence: float = 0.0
    inactive_seconds: float = 0.0
    reclined_ratio: float = 0.0
    motion_score: float = 0.0
    pose_visible: bool = False
    pose_landmarks: object = None    # raw MediaPipe landmarks — for drawing
    debug: dict = field(default_factory=dict)


class MotionDetector:
    def __init__(self, history=6):
        self._frames = []
        self._history = history

    def update(self, gray: np.ndarray) -> float:
        import cv2
        small = cv2.resize(gray, (64, 48)).astype(np.float32)
        self._frames.append(small)
        if len(self._frames) > self._history:
            self._frames.pop(0)
        if len(self._frames) < 2:
            return 0.0
        return float(np.abs(self._frames[-1] - self._frames[-2]).mean())


class InactivityTimer:
    def __init__(self):
        self._last_move = time.monotonic()

    def update(self, motion_score: float) -> float:
        if motion_score > MOTION_THRESHOLD:
            self._last_move = time.monotonic()
        return time.monotonic() - self._last_move

    def reset(self):
        self._last_move = time.monotonic()


def _lm(landmarks, idx, w, h):
    lm = landmarks.landmark[idx]
    if lm.visibility < POSE_LANDMARK_MIN_VISIBILITY:
        return None
    return lm.x * w, lm.y * h


def compute_recline_ratio(landmarks, w, h):
    pts = []
    for idx in [_NOSE,_L_SHOULDER,_R_SHOULDER,_L_HIP,_R_HIP,
                _L_KNEE,_R_KNEE,_L_ANKLE,_R_ANKLE]:
        p = _lm(landmarks, idx, w, h)
        if p:
            pts.append(p)
    if len(pts) < 4:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x_span = max(xs)-min(xs); y_span = max(ys)-min(ys)
    total = x_span + y_span
    return float(x_span / total) if total > 10 else None


class SleepPoseDetector:
    """
    Camera-agnostic sleep detector. All thresholds from config/env.

    Detection paths:
      PRIMARY  — inactive >= SLEEP_SECONDS                  → sleeping
      BOOSTER  — recline >= RECLINE_THRESHOLD
                 AND inactive >= SLEEP_SECONDS_RECLINED     → sleeping (faster)
      DROWSY   — inactive >= DROWSY_SECONDS
                 OR recline >= RECLINE_MIN                  → drowsy
    """

    def __init__(self):
        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=POSE_DETECTION_CONFIDENCE,
            min_tracking_confidence=POSE_TRACKING_CONFIDENCE,
        )
        self._motion     = MotionDetector()
        self._inactivity = InactivityTimer()
        self._last_pose_time = time.monotonic()
        self._recline_history: list[float] = []

    def process(self, bgr_frame: np.ndarray) -> SleepAnalysis:
        import cv2
        h, w = bgr_frame.shape[:2]

        gray   = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        motion = self._motion.update(gray)
        inactive_secs = self._inactivity.update(motion)

        rgb    = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        result = self._pose.process(rgb)

        if result.pose_landmarks is None:
            gap   = time.monotonic() - self._last_pose_time
            state = "no_person" if gap > 3.0 else "unknown"
            return SleepAnalysis(
                state=state,
                inactive_seconds=round(inactive_secs, 1),
                motion_score=round(motion, 2),
                pose_visible=False,
                pose_landmarks=None,
                debug={"pose": "none", "gap_s": round(gap, 1)},
            )

        self._last_pose_time = time.monotonic()
        lms = result.pose_landmarks

        recline = compute_recline_ratio(lms, w, h)
        if recline is not None:
            self._recline_history.append(recline)
            if len(self._recline_history) > RECLINE_SMOOTH_FRAMES:
                self._recline_history.pop(0)

        smooth_recline    = float(np.mean(self._recline_history)) if self._recline_history else 0.0
        clearly_reclined  = smooth_recline >= RECLINE_THRESHOLD
        somewhat_reclined = smooth_recline >= RECLINE_MIN

        sleeping_by_inactivity = inactive_secs >= SLEEP_SECONDS
        sleeping_by_recline    = clearly_reclined and inactive_secs >= SLEEP_SECONDS_RECLINED
        sleeping = sleeping_by_inactivity or sleeping_by_recline

        drowsy = not sleeping and (inactive_secs >= DROWSY_SECONDS or somewhat_reclined)

        if sleeping:
            state      = "sleeping"
            inact_conf = min(1.0, inactive_secs / SLEEP_SECONDS)
            recl_conf  = min(1.0, smooth_recline / RECLINE_THRESHOLD) if RECLINE_THRESHOLD > 0 else 0.5
            confidence = min(1.0, (inact_conf + recl_conf) / 2 + 0.1)
            trigger    = "inactivity" if sleeping_by_inactivity else "recline"
        elif drowsy:
            state      = "drowsy"
            confidence = 0.4 + 0.4 * min(1.0, inactive_secs / DROWSY_SECONDS)
            trigger    = "drowsy"
        else:
            state      = "awake"
            confidence = max(0.0, 1.0 - (inactive_secs / SLEEP_SECONDS))
            trigger    = "awake"

        return SleepAnalysis(
            state=state,
            confidence=round(confidence, 3),
            inactive_seconds=round(inactive_secs, 1),
            reclined_ratio=round(smooth_recline, 3),
            motion_score=round(motion, 2),
            pose_visible=True,
            pose_landmarks=lms,    # pass through for drawing — no re-processing
            debug={
                "raw_recline":      round(recline, 3) if recline else None,
                "smooth_recline":   round(smooth_recline, 3),
                "clearly_reclined": clearly_reclined,
                "inactive_s":       round(inactive_secs, 1),
                "motion":           round(motion, 2),
                "trigger":          trigger,
            },
        )

    def close(self):
        self._pose.close()
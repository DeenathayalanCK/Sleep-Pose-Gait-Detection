import os
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

import time
import logging
import numpy as np
import mediapipe as mp
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── MediaPipe landmark indices ────────────────────────────────────────────────
# Pose
_NOSE         = 0
_L_SHOULDER   = 11
_R_SHOULDER   = 12
_L_HIP        = 23
_R_HIP        = 24
_L_KNEE       = 25
_R_KNEE       = 26
_L_ANKLE      = 27
_R_ANKLE      = 28
_L_WRIST      = 15
_R_WRIST      = 16
_L_EAR        = 7
_R_EAR        = 8

# ── Result dataclass ──────────────────────────────────────────────────────────
@dataclass
class SleepAnalysis:
    state: str = "unknown"          # "sleeping" | "drowsy" | "awake" | "no_person"
    confidence: float = 0.0         # 0.0 – 1.0
    inactive_seconds: float = 0.0
    reclined_ratio: float = 0.0     # how horizontal the body is (0=upright, 1=flat)
    motion_score: float = 0.0       # recent motion amount (0 = still)
    pose_visible: bool = False
    debug: dict = field(default_factory=dict)


# ── Background subtraction for motion ────────────────────────────────────────
class MotionDetector:
    """
    Frame-differencing motion detector scoped to a person's bounding region.
    Works even when MediaPipe loses the skeleton.
    """
    def __init__(self, history: int = 8):
        self._frames: list[np.ndarray] = []
        self._history = history

    def update(self, gray_roi: np.ndarray) -> float:
        """Returns mean absolute per-pixel change (0 = no motion)."""
        small = self._resize(gray_roi)
        self._frames.append(small.astype(np.float32))
        if len(self._frames) > self._history:
            self._frames.pop(0)
        if len(self._frames) < 2:
            return 0.0
        diff = np.abs(self._frames[-1] - self._frames[-2])
        return float(diff.mean())

    @staticmethod
    def _resize(img: np.ndarray, w: int = 64, h: int = 48) -> np.ndarray:
        import cv2
        return cv2.resize(img, (w, h))


# ── Inactivity timer ──────────────────────────────────────────────────────────
class InactivityTimer:
    MOTION_THRESHOLD = 1.2   # pixel intensity units — tune per scene

    def __init__(self):
        self._last_move = time.monotonic()

    def update(self, motion_score: float) -> float:
        """Returns seconds since last significant movement."""
        if motion_score > self.MOTION_THRESHOLD:
            self._last_move = time.monotonic()
        return time.monotonic() - self._last_move

    def reset(self):
        self._last_move = time.monotonic()


# ── Recline classifier ────────────────────────────────────────────────────────
def _safe_lm(landmarks, idx, w: int, h: int) -> Optional[tuple[float, float, float]]:
    """Return (x_px, y_px, visibility) or None if not visible enough."""
    lm = landmarks.landmark[idx]
    if lm.visibility < 0.35:
        return None
    return lm.x * w, lm.y * h, lm.visibility


def compute_recline_ratio(landmarks, w: int, h: int) -> Optional[float]:
    """
    Measures how horizontal the torso + leg chain is.

    From a top-down CCTV view a sleeping/reclined person appears stretched
    horizontally across the frame — the Y-spread of their body parts is large
    relative to the X-spread.  An upright seated or standing person has a
    compact vertical arrangement.

    Returns 0.0 (upright) → 1.0 (flat/reclined), or None if not enough
    landmarks are visible.
    """
    pts = []
    for idx in [_NOSE, _L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP,
                _L_KNEE, _R_KNEE, _L_ANKLE, _R_ANKLE]:
        r = _safe_lm(landmarks, idx, w, h)
        if r:
            pts.append((r[0], r[1]))

    if len(pts) < 4:
        return None

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)

    total = x_span + y_span
    if total < 10:
        return None

    # For a top-down camera: sleeping person is spread along X (horizontal
    # in camera frame), awake/sitting person is more compact or spread in Y.
    return float(x_span / total)   # 0.5 = square, >0.6 = reclined


def compute_head_drop(landmarks, w: int, h: int) -> Optional[float]:
    """
    In a top-down view, when someone reclines their head moves away from their
    torso (further from the desk edge).  We measure how far the nose Y is from
    the shoulder midpoint Y — positive means head is below shoulders in frame.
    Returns normalised value 0–1.
    """
    nose      = _safe_lm(landmarks, _NOSE, w, h)
    l_shoulder = _safe_lm(landmarks, _L_SHOULDER, w, h)
    r_shoulder = _safe_lm(landmarks, _R_SHOULDER, w, h)

    if not (nose and (l_shoulder or r_shoulder)):
        return None

    shoulder_y_vals = [s[1] for s in [l_shoulder, r_shoulder] if s]
    shoulder_y = sum(shoulder_y_vals) / len(shoulder_y_vals)

    drop = (nose[1] - shoulder_y) / h   # normalised to frame height
    return float(drop)


# ── Main detector ─────────────────────────────────────────────────────────────
class SleepPoseDetector:
    """
    Primary sleep-detection pipeline for top-down CCTV footage.

    Detection logic (in priority order):
    1. No pose detected for >3s  →  person absent or occluded
    2. Recline ratio > 0.62 AND inactive > SLEEP_SECONDS  →  sleeping
    3. Recline ratio > 0.55 OR inactive > DROWSY_SECONDS  →  drowsy
    4. Otherwise  →  awake
    """

    SLEEP_SECONDS  = 10.0   # confirmed still + reclined → sleeping
    DROWSY_SECONDS = 5.0    # borderline → drowsy

    # Recline thresholds (tuned for top-down CCTV)
    RECLINE_SLEEP  = 0.60
    RECLINE_DROWSY = 0.52

    def __init__(self):
        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.45,
            min_tracking_confidence=0.45,
        )
        self._motion    = MotionDetector(history=6)
        self._inactivity = InactivityTimer()
        self._last_pose_time = time.monotonic()

        # Smoothing: keep last N recline values to avoid single-frame flicker
        self._recline_history: list[float] = []
        self._SMOOTH = 8

    def process(self, bgr_frame: np.ndarray) -> SleepAnalysis:
        import cv2

        h, w = bgr_frame.shape[:2]
        rgb  = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        result = self._pose.process(rgb)

        # ── Motion (works regardless of pose visibility) ──────────────────
        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        motion = self._motion.update(gray)
        inactive_secs = self._inactivity.update(motion)

        # ── No person / pose lost ─────────────────────────────────────────
        if result.pose_landmarks is None:
            gap = time.monotonic() - self._last_pose_time
            state = "no_person" if gap > 3.0 else "unknown"
            return SleepAnalysis(
                state=state,
                confidence=0.0,
                inactive_seconds=inactive_secs,
                motion_score=motion,
                pose_visible=False,
                debug={"pose": "none", "gap_s": round(gap, 1)},
            )

        self._last_pose_time = time.monotonic()
        lms = result.pose_landmarks

        # ── Recline ratio ─────────────────────────────────────────────────
        recline = compute_recline_ratio(lms, w, h)
        head_drop = compute_head_drop(lms, w, h)

        if recline is not None:
            self._recline_history.append(recline)
            if len(self._recline_history) > self._SMOOTH:
                self._recline_history.pop(0)

        smooth_recline = (
            float(np.mean(self._recline_history))
            if self._recline_history else 0.0
        )

        # ── Classify state ────────────────────────────────────────────────
        sleeping = (
            smooth_recline >= self.RECLINE_SLEEP
            and inactive_secs >= self.SLEEP_SECONDS
        )
        drowsy = (
            not sleeping and (
                smooth_recline >= self.RECLINE_DROWSY
                or inactive_secs >= self.DROWSY_SECONDS
            )
        )

        if sleeping:
            state = "sleeping"
            confidence = min(1.0, (inactive_secs / self.SLEEP_SECONDS) *
                            (smooth_recline / self.RECLINE_SLEEP))
        elif drowsy:
            state = "drowsy"
            confidence = 0.5 + 0.3 * min(1.0, inactive_secs / self.DROWSY_SECONDS)
        else:
            state = "awake"
            confidence = 1.0 - min(1.0, inactive_secs / self.SLEEP_SECONDS)

        return SleepAnalysis(
            state=state,
            confidence=round(confidence, 3),
            inactive_seconds=round(inactive_secs, 1),
            reclined_ratio=round(smooth_recline, 3),
            motion_score=round(motion, 2),
            pose_visible=True,
            debug={
                "raw_recline": round(recline, 3) if recline else None,
                "smooth_recline": round(smooth_recline, 3),
                "head_drop": round(head_drop, 3) if head_drop else None,
                "motion": round(motion, 2),
                "inactive_s": round(inactive_secs, 1),
            },
        )

    def close(self):
        self._pose.close()
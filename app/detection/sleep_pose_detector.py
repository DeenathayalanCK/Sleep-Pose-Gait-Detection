import os
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

import time
import logging
import numpy as np
import mediapipe as mp
from collections import deque
from dataclasses import dataclass, field

from app.config import (
    MOTION_THRESHOLD, SLEEP_SECONDS, DROWSY_SECONDS,
    SLEEP_SECONDS_RECLINED, RECLINE_THRESHOLD, RECLINE_MIN,
    POSE_DETECTION_CONFIDENCE, POSE_TRACKING_CONFIDENCE,
    POSE_LANDMARK_MIN_VISIBILITY, RECLINE_SMOOTH_FRAMES,
)
from app.detection.body_signals import extract_body_signals
from app.detection.ear_integrator import EARIntegrator, EARResult

logger = logging.getLogger(__name__)

_NOSE=0; _L_SHOULDER=11; _R_SHOULDER=12
_L_HIP=23; _R_HIP=24; _L_KNEE=25; _R_KNEE=26
_L_ANKLE=27; _R_ANKLE=28; _L_WRIST=15; _R_WRIST=16

# ── Calibrated thresholds (can be overridden per .env or calibration DB) ──────
# These are defaults that work for a side-mounted office camera.
# The calibration tool writes camera-specific values to .env.
_HEAD_DROP_DROWSY   = float(os.getenv("HEAD_DROP_DROWSY_DEG",   "40.0"))  # degrees — raised for top-angle camera
_HEAD_DROP_SLEEP    = float(os.getenv("HEAD_DROP_SLEEP_DEG",    "55.0"))  # degrees — raised: top-angle camera reads 40-50° for normal forward lean
_HEAD_TILT_SLEEP    = float(os.getenv("HEAD_TILT_SLEEP_DEG",    "35.0"))  # degrees lateral
_SPINE_DROWSY       = float(os.getenv("SPINE_DROWSY_DEG",       "30.0"))  # degrees from vertical
_SPINE_SLEEP        = float(os.getenv("SPINE_SLEEP_DEG",        "50.0"))  # degrees from vertical
_WRIST_ACTIVE_MIN   = float(os.getenv("WRIST_ACTIVE_MIN",       "0.005")) # min wrist movement = typing
_SMOOTH_WINDOW      = int(os.getenv("SIGNAL_SMOOTH_FRAMES",     "10"))    # frames to smooth signals


@dataclass
class SleepAnalysis:
    state:            str   = "unknown"
    confidence:       float = 0.0
    inactive_seconds: float = 0.0
    reclined_ratio:   float = 0.0
    motion_score:     float = 0.0
    pose_visible:     bool  = False
    pose_landmarks:   object = None
    debug:            dict  = field(default_factory=dict)
    signals:          dict  = field(default_factory=dict)  # raw body signals
    ear:              object = None   # EARResult — None if face not visible


class MotionDetector:
    def __init__(self, history=6):
        self._frames  = []
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


class SignalSmoother:
    """
    Smooths any float signal over a rolling window.
    Eliminates per-frame noise that causes state flickering.
    """
    def __init__(self, window: int = 10):
        self._buf: deque = deque(maxlen=window)

    def update(self, value: float | None) -> float | None:
        if value is None:
            return None
        self._buf.append(value)
        return float(np.mean(self._buf))

    def mean(self) -> float | None:
        return float(np.mean(self._buf)) if self._buf else None


def _lm(landmarks, idx, w, h):
    lm = landmarks.landmark[idx]
    if lm.visibility < POSE_LANDMARK_MIN_VISIBILITY:
        return None
    return lm.x * w, lm.y * h


def compute_recline_ratio(landmarks, w, h):
    pts = []
    for idx in [_NOSE, _L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP,
                _L_KNEE, _R_KNEE, _L_ANKLE, _R_ANKLE]:
        p = _lm(landmarks, idx, w, h)
        if p:
            pts.append(p)
    if len(pts) < 4:
        return None
    xs     = [p[0] for p in pts]
    ys     = [p[1] for p in pts]
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)
    total  = x_span + y_span
    return float(x_span / total) if total > 10 else None


class SleepPoseDetector:
    """
    Multi-signal fatigue detector.

    SIGNALS USED (all smoothed over rolling window):
      1. Inactivity timer           — body not moving
      2. Recline ratio              — body orientation (proxy for lying down)
      3. Spine angle                — NEW: torso tilt from vertical
      4. Head drop angle            — NEW: head drooping forward
      5. Head lateral tilt          — NEW: head fallen sideways
      6. Wrist activity             — NEW: hands moving = typing = awake

    DECISION (multi-signal fusion):
      SLEEPING if ANY of:
        • inactivity >= SLEEP_SECONDS
        • recline >= RECLINE_THRESHOLD + inactivity >= SLEEP_SECONDS_RECLINED
        • head_drop >= HEAD_DROP_SLEEP + inactivity >= DROWSY_SECONDS
        • head_tilt >= HEAD_TILT_SLEEP  (head fallen sideways)
        • spine_angle >= SPINE_SLEEP + inactivity >= DROWSY_SECONDS

      DROWSY if ANY of:
        • inactivity >= DROWSY_SECONDS + (recline OR head_drop)
        • head_drop >= HEAD_DROP_DROWSY + some inactivity
        • spine_angle >= SPINE_DROWSY + inactivity >= DROWSY_SECONDS/2

      WRIST OVERRIDE: if wrist_activity > WRIST_ACTIVE_MIN → never sleeping/drowsy
        (actively typing hands prove wakefulness regardless of head/spine signals)
    """

    def __init__(self):
        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=POSE_DETECTION_CONFIDENCE,
            min_tracking_confidence=POSE_TRACKING_CONFIDENCE,
        )
        self._motion           = MotionDetector()
        self._inactivity       = InactivityTimer()
        self._last_pose_time   = time.monotonic()
        self._recline_history  = []
        self._prev_wrist_pos   = None

        # EAR / PERCLOS tracker
        self._ear = EARIntegrator()

        # Per-signal smoothers
        self._sm_head_drop  = SignalSmoother(_SMOOTH_WINDOW)
        self._sm_head_tilt  = SignalSmoother(_SMOOTH_WINDOW)
        self._sm_spine      = SignalSmoother(_SMOOTH_WINDOW)
        self._sm_wrist      = SignalSmoother(_SMOOTH_WINDOW)
        self._sm_recline    = SignalSmoother(RECLINE_SMOOTH_FRAMES)

    def process(self, bgr_frame: np.ndarray) -> SleepAnalysis:
        import cv2
        h, w = bgr_frame.shape[:2]

        gray          = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        motion        = self._motion.update(gray)
        inactive_secs = self._inactivity.update(motion)

        rgb    = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        result = self._pose.process(rgb)

        # ── EAR / PERCLOS (independent of pose) ──────────────────────
        ear_result = self._ear.process(bgr_frame)

        if result.pose_landmarks is None:
            gap   = time.monotonic() - self._last_pose_time
            state = "no_person" if gap > 3.0 else "unknown"
            return SleepAnalysis(
                state=state,
                inactive_seconds=round(inactive_secs, 1),
                motion_score=round(motion, 2),
                pose_visible=False,
                debug={"pose": "none", "gap_s": round(gap, 1)},
            )

        self._last_pose_time = time.monotonic()
        lms = result.pose_landmarks

        # ── Extract and smooth all body signals ───────────────────────
        raw_sigs = extract_body_signals(lms, self._prev_wrist_pos)
        self._prev_wrist_pos = raw_sigs.get("wrist_pos")

        head_drop  = self._sm_head_drop.update(raw_sigs["head_drop_angle"])
        head_tilt  = self._sm_head_tilt.update(raw_sigs["head_tilt_angle"])
        spine_ang  = self._sm_spine.update(raw_sigs["spine_angle"])
        wrist_act  = self._sm_wrist.update(raw_sigs["wrist_activity"])

        # ── Recline ratio (existing, keep for backward compat) ────────
        raw_recline = compute_recline_ratio(lms, w, h)
        smooth_recline = self._sm_recline.update(raw_recline) or 0.0

        clearly_reclined  = smooth_recline >= RECLINE_THRESHOLD
        somewhat_reclined = smooth_recline >= RECLINE_MIN

        # ── Wrist activity override ────────────────────────────────────
        # If hands are actively moving → person is awake (typing, working)
        # This is the most reliable anti-false-positive signal we have.
        wrist_active = (wrist_act is not None and wrist_act > _WRIST_ACTIVE_MIN)

        # ── EAR / PERCLOS signal integration ─────────────────────────
        sleep_by_ear  = ear_result.sleep_by_ear   if ear_result else False
        drowsy_by_ear = ear_result.drowsy_by_ear  if ear_result else False

        # ── Multi-signal sleeping detection ───────────────────────────
        sleep_by_inactivity = inactive_secs >= SLEEP_SECONDS
        sleep_by_recline    = clearly_reclined and inactive_secs >= SLEEP_SECONDS_RECLINED
        # Head drop sleeping: requires HIGH angle + LONG inactivity + corroboration
        # Top-angle cameras produce inflated head_drop values for forward lean.
        # Require at least one other signal to confirm it's sleep, not reading.
        _wrist_idle = (wrist_act is None or wrist_act <= _WRIST_ACTIVE_MIN)
        _corroborated = (
            somewhat_reclined or                          # body leaning back
            (ear_result and ear_result.perclos >= 0.10)  # any eye closure
        )
        sleep_by_head_drop  = (
            head_drop is not None
            and head_drop >= _HEAD_DROP_SLEEP
            and inactive_secs >= SLEEP_SECONDS           # full sleep threshold, not drowsy
            and _wrist_idle                              # hands not moving
            and _corroborated                            # at least 1 more signal agrees
        )
        sleep_by_head_tilt  = (
            head_tilt is not None
            and head_tilt >= _HEAD_TILT_SLEEP
            and inactive_secs >= DROWSY_SECONDS
        )
        sleep_by_spine      = (
            spine_ang is not None
            and spine_ang >= _SPINE_SLEEP
            and inactive_secs >= DROWSY_SECONDS
        )

        sleeping = (
            sleep_by_inactivity or sleep_by_recline or
            sleep_by_head_drop  or sleep_by_head_tilt or sleep_by_spine or
            sleep_by_ear        # PERCLOS >= 40% = strong sleep signal
        ) and not wrist_active

        # ── Multi-signal drowsy detection ─────────────────────────────
        drowsy_by_inactivity_recline = (
            inactive_secs >= DROWSY_SECONDS and somewhat_reclined
        )
        drowsy_by_inactivity_alone = inactive_secs >= DROWSY_SECONDS * 1.5
        # Drowsy head drop: wrist must be idle — typing with head forward is normal
        drowsy_by_head_drop = (
            head_drop is not None
            and head_drop >= _HEAD_DROP_DROWSY
            and inactive_secs >= DROWSY_SECONDS          # full drowsy window, not half
            and _wrist_idle                              # not typing
        )
        drowsy_by_spine = (
            spine_ang is not None
            and spine_ang >= _SPINE_DROWSY
            and inactive_secs >= DROWSY_SECONDS * 0.5
        )

        drowsy = (
            not sleeping and (
                drowsy_by_inactivity_recline or
                drowsy_by_inactivity_alone   or
                drowsy_by_head_drop          or
                drowsy_by_spine              or
                drowsy_by_ear               # PERCLOS >= 15%
            ) and not wrist_active
        )

        # ── Confidence scoring ────────────────────────────────────────
        if sleeping:
            # More signals firing = higher confidence
            signals_firing = sum([
                sleep_by_inactivity, sleep_by_recline,
                sleep_by_head_drop, sleep_by_head_tilt,
                sleep_by_spine, sleep_by_ear
            ])
            confidence = min(1.0, 0.5 + signals_firing * 0.15)
            trigger    = (
                "perclos"    if sleep_by_ear       else
                "head_drop"  if sleep_by_head_drop else
                "head_tilt"  if sleep_by_head_tilt else
                "spine"      if sleep_by_spine     else
                "recline"    if sleep_by_recline   else
                "inactivity"
            )
            state = "sleeping"

        elif drowsy:
            signals_firing = sum([
                drowsy_by_inactivity_recline, drowsy_by_head_drop, drowsy_by_spine
            ])
            confidence = min(1.0, 0.35 + signals_firing * 0.2)
            trigger    = (
                "perclos"   if drowsy_by_ear       else
                "head_drop" if drowsy_by_head_drop else
                "spine"     if drowsy_by_spine     else
                "drowsy"
            )
            state = "drowsy"

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
            pose_landmarks=lms,
            ear=ear_result,
            signals={
                # EAR / PERCLOS
                "perclos":            ear_result.perclos     if ear_result and ear_result.face_found else None,
                "ear":                ear_result.ear         if ear_result and ear_result.face_found else None,
                "eyes_closed":        ear_result.eyes_closed if ear_result and ear_result.face_found else None,
                # Fatigue signals (smoothed)
                "head_drop_angle":    head_drop,
                "head_tilt_angle":    head_tilt,
                "spine_angle":        spine_ang,
                "wrist_active":       wrist_active,
                "recline":            round(smooth_recline, 3),
                # Posture signals (raw — needed by calibration tool)
                "knee_hip_y_gap":     raw_sigs.get("knee_hip_y_gap"),
                "knee_hip_x_gap":     raw_sigs.get("knee_hip_x_gap"),
                "torso_compactness":  raw_sigs.get("torso_compactness"),
                "sh_hip_y_gap":       raw_sigs.get("sh_hip_y_gap"),
                "shoulder_ear_ratio": raw_sigs.get("shoulder_ear_ratio"),
                "wrist_activity":     raw_sigs.get("wrist_activity"),
            },
            debug={
                "trigger":          trigger,
                "inactive_s":       round(inactive_secs, 1),
                "motion":           round(motion, 2),
                "smooth_recline":   round(smooth_recline, 3),
                "head_drop":        round(head_drop, 1) if head_drop else None,
                "head_tilt":        round(head_tilt, 1) if head_tilt else None,
                "spine_angle":      round(spine_ang, 1) if spine_ang else None,
                "wrist_active":     wrist_active,
                "sleep_flags": {
                    "inactivity": sleep_by_inactivity,
                    "recline":    sleep_by_recline,
                    "head_drop":  sleep_by_head_drop,
                    "head_tilt":  sleep_by_head_tilt,
                    "spine":      sleep_by_spine,
                },
            },
        )

    def close(self):
        self._pose.close()
        self._ear.close()
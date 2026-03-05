"""
TrackManager — one SleepPoseDetector + FatigueEngine + centroid history per track.

KEY FIXES in this version:
  • WALKING false positive: motion was crop-level jitter, not real person movement.
    Now tracks bbox centroid displacement across frames — only "walking" if the
    person's position in the frame actually changes significantly over N frames.
  • INACTIVE state: shown when person has been sitting/standing still for
    INACTIVE_DISPLAY_SECONDS (separate from the sleep detection threshold).
  • UNKNOWN reduced: "unknown" only when pose truly can't be assessed.
"""
import time
import datetime
import logging
from collections import deque
from dataclasses import dataclass, field

from app.config import (
    TRACK_TIMEOUT_SECONDS, TRACK_REENTRY_SECONDS,
    MAX_POSE_PERSONS, CAMERA_ID, SLEEP_SECONDS,
)
from app.detection.sleep_pose_detector import SleepPoseDetector, SleepAnalysis
from app.engine.fatigue_engine import FatigueEngine
from app.engine.state_analyzer import StateAnalyzer

logger = logging.getLogger(__name__)

# How many consecutive frames of centroid movement to confirm "walking"
_WALK_CENTROID_FRAMES    = 4       # must move for N consecutive frames
_WALK_CENTROID_PX        = 8       # pixels of centroid shift per frame to count
# How many seconds still (not sleeping) before showing "inactive" label
_INACTIVE_DISPLAY_SECS   = 5.0


@dataclass
class PersonState:
    track_id:        int
    detector:        SleepPoseDetector
    engine:          FatigueEngine
    state_analyzer:  StateAnalyzer
    last_seen:       float = field(default_factory=time.monotonic)
    analysis:        SleepAnalysis = field(default_factory=SleepAnalysis)
    state:           str = "unknown"
    session_start:   str = field(
        default_factory=lambda: datetime.datetime.now().isoformat(
            sep=" ", timespec="seconds"
        )
    )
    frame_dt:        float = 0.033
    # Centroid history for real walk detection (deque of (cx, cy))
    centroid_hist:   deque = field(
        default_factory=lambda: deque(maxlen=_WALK_CENTROID_FRAMES + 1)
    )
    # How many recent frames had significant centroid movement
    walk_frame_count: int = 0


class TrackManager:
    def __init__(self):
        self._states: dict[int, PersonState] = {}

    def update(self, persons: list, frame,
               annotated_frame=None) -> dict[int, "PersonState"]:
        from app.database.repository import upsert_person_session

        now    = time.monotonic()
        now_dt = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")

        persons_sorted = sorted(persons, key=lambda p: p.area, reverse=True)
        pose_budget    = MAX_POSE_PERSONS
        active_ids     = set()
        fh, fw         = frame.shape[:2]

        for person in persons_sorted:
            tid = person.track_id
            active_ids.add(tid)

            if tid not in self._states:
                self._states[tid] = PersonState(
                    track_id       = tid,
                    detector       = SleepPoseDetector(),
                    engine         = FatigueEngine(person_id=tid),
                    state_analyzer = StateAnalyzer(),
                    session_start  = now_dt,
                )
                logger.info(f"New person tracked: ID={tid}")

            ps = self._states[tid]
            ps.last_seen = now

            # ── Centroid-based real walk detection ─────────────────────
            cx, cy = person.center
            ps.centroid_hist.append((cx, cy))

            real_walking = False
            if len(ps.centroid_hist) >= 2:
                # Count frames where centroid moved significantly
                move_frames = sum(
                    1 for i in range(1, len(ps.centroid_hist))
                    if (abs(ps.centroid_hist[i][0] - ps.centroid_hist[i-1][0])
                        + abs(ps.centroid_hist[i][1] - ps.centroid_hist[i-1][1]))
                    > _WALK_CENTROID_PX
                )
                # Walking = centroid moved in majority of recent frames
                real_walking = move_frames >= max(2, _WALK_CENTROID_FRAMES - 1)

            # ── Pose analysis on crop ──────────────────────────────────
            if pose_budget > 0:
                crop = person.crop(frame, pad=20)
                if crop.size > 0:
                    analysis  = ps.detector.process(crop)
                    analysis  = _remap_landmarks(analysis, person, crop.shape, fh, fw)
                    ps.analysis = analysis
                    pose_budget -= 1

            # ── Final state resolution ─────────────────────────────────
            pose_st  = ps.analysis.state
            inactive_secs = ps.analysis.inactive_seconds

            # Sleep/drowsy always win
            if pose_st in ("sleeping", "drowsy"):
                ps.state = pose_st

            elif real_walking:
                # Person's bbox centroid is actually moving → walking
                ps.state = "walking"

            else:
                # Person is not walking — classify posture
                # Pass motion_score=0 to prevent crop-jitter walking override
                posture = ps.state_analyzer.analyze(
                    pose_state     = pose_st,
                    inactive       = inactive_secs > SLEEP_SECONDS,
                    pose_landmarks = ps.analysis.pose_landmarks,
                    frame_h        = fh,
                    frame_w        = fw,
                    motion_score   = 0.0,   # force no-walk; centroid already checked
                )

                # Layer inactive on top of sitting/standing if still long enough
                if posture in ("sitting", "standing", "awake", "unknown") \
                   and inactive_secs >= _INACTIVE_DISPLAY_SECS \
                   and pose_st not in ("sleeping", "drowsy"):
                    base    = posture if posture in ("sitting", "standing") else "sitting"
                    ps.state = f"{base}_inactive"
                else:
                    ps.state = posture

            upsert_person_session(
                track_id=tid, camera_id=CAMERA_ID,
                now_dt=now_dt, state=ps.state,
                elapsed=ps.frame_dt,
            )

            ps.engine.update(
                ps.analysis,
                snapshot_frame=annotated_frame,
                person_bbox=(person.x1, person.y1, person.x2, person.y2),
            )

        # ── Garbage-collect absent tracks ──────────────────────────────
        for tid in list(self._states.keys()):
            if tid not in active_ids:
                ps     = self._states[tid]
                absent = now - ps.last_seen
                if absent > TRACK_REENTRY_SECONDS:
                    logger.info(f"Track ID={tid} expired after {absent:.0f}s")
                    ps.detector.close()
                    del self._states[tid]

        return {tid: self._states[tid] for tid in active_ids if tid in self._states}


def _remap_landmarks(analysis, person, crop_shape, frame_h, frame_w):
    if analysis.pose_landmarks is None:
        return analysis
    ch, cw = crop_shape[:2]
    pad    = 20
    ox     = max(0, person.x1 - pad)
    oy     = max(0, person.y1 - pad)
    for lm in analysis.pose_landmarks.landmark:
        lm.x = (lm.x * cw + ox) / frame_w
        lm.y = (lm.y * ch + oy) / frame_h
    return analysis
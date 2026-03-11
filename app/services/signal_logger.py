"""
signal_logger.py — Per-frame signal recorder for ML training data collection.

Writes one CSV row every LOG_EVERY_FRAMES frames per person.
Default: every 30 frames ≈ every 2 seconds at ~15fps processing rate.

CSV columns:
  timestamp       — wall-clock ISO time of the frame
  video_pos_sec   — position in source video (seconds) — KEY for labelling
  person_id       — track ID
  camera_id       — from config
  head_drop_angle, spine_angle, head_tilt_angle
  wrist_activity, recline, perclos, ear
  inactive_seconds, motion_score, shoulder_ear_ratio
  z_max, z_baseline_ready
  system_state    — what the rule engine decided this frame
  true_label      — BLANK — you fill this in during labelling

Usage:
  from app.services.signal_logger import SignalLogger
  logger = SignalLogger()
  # in main monitor loop, after analysis:
  logger.log(person_id=tid, analysis=ps.analysis, video_pos_sec=pos)
  # at shutdown:
  logger.close()
"""
import os
import csv
import datetime
import threading
import logging
from app.config import CAMERA_ID

logger = logging.getLogger(__name__)

# Log every N frames per person (30 ≈ 2s at ~15fps)
_LOG_EVERY = int(os.getenv("SIGNAL_LOG_EVERY_FRAMES", "30"))
_LOG_DIR   = os.getenv("SIGNAL_LOG_DIR", "data/signals")

# CSV columns written per row
_FIELDNAMES = [
    "timestamp", "video_pos_sec", "person_id", "camera_id",
    # Core fatigue signals
    "head_drop_angle", "spine_angle", "head_tilt_angle",
    "wrist_activity", "recline", "perclos", "ear",
    "inactive_seconds", "motion_score", "shoulder_ear_ratio",
    # Z-score baseline
    "z_max", "z_baseline_ready",
    # System decision
    "system_state",
    # Ground truth — blank until you label it
    "true_label",
]


class SignalLogger:
    """
    Thread-safe CSV logger. One file per day.
    Writes one row every LOG_EVERY_FRAMES frames per tracked person.
    """

    def __init__(self):
        os.makedirs(_LOG_DIR, exist_ok=True)
        self._lock      = threading.Lock()
        self._counters  = {}   # person_id → frame counter
        self._file      = None
        self._writer    = None
        self._filepath  = None
        self._open_file()
        logger.info(
            f"SignalLogger started → {self._filepath} "
            f"(1 row per {_LOG_EVERY} frames per person)"
        )

    def _open_file(self):
        date      = datetime.date.today().isoformat()
        fname     = f"signals_{date}.csv"
        fpath     = os.path.join(_LOG_DIR, fname)
        existed   = os.path.exists(fpath)
        self._filepath = fpath
        self._file     = open(fpath, "a", newline="", buffering=1)
        self._writer   = csv.DictWriter(
            self._file, fieldnames=_FIELDNAMES, extrasaction="ignore"
        )
        if not existed:
            self._writer.writeheader()

    def log(self, person_id: int, analysis, video_pos_sec: float = None):
        """
        Call once per frame per person in the main monitor loop.

        Args:
            person_id:     track ID
            analysis:      SleepAnalysis object from SleepPoseDetector
            video_pos_sec: current position in source video in seconds
                           (from cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)
                           Pass None for live RTSP streams.
        """
        if analysis is None:
            return

        # Throttle — only write every _LOG_EVERY frames per person
        with self._lock:
            cnt = self._counters.get(person_id, 0) + 1
            self._counters[person_id] = cnt
            if cnt % _LOG_EVERY != 0:
                return

        sigs = analysis.signals or {}
        z    = analysis.z_score

        row = {
            "timestamp":       datetime.datetime.now().isoformat(sep=" ",
                                                                  timespec="seconds"),
            "video_pos_sec":   round(video_pos_sec, 1) if video_pos_sec is not None else "",
            "person_id":       person_id,
            "camera_id":       CAMERA_ID,
            # Fatigue signals
            "head_drop_angle": _r(sigs.get("head_drop_angle")),
            "spine_angle":     _r(sigs.get("spine_angle")),
            "head_tilt_angle": _r(sigs.get("head_tilt_angle")),
            "wrist_activity":  _r(sigs.get("wrist_activity"), 4),
            "recline":         _r(sigs.get("recline"), 3),
            "perclos":         _r(sigs.get("perclos"), 3),
            "ear":             _r(sigs.get("ear"), 3),
            "inactive_seconds":_r(analysis.inactive_seconds, 1),
            "motion_score":    _r(analysis.motion_score, 2),
            "shoulder_ear_ratio": _r(sigs.get("shoulder_ear_ratio"), 3),
            # Z-score
            "z_max":           _r(z.max_z if z else None, 2),
            "z_baseline_ready":1 if (z and z.baseline_ready) else 0,
            # System label
            "system_state":    analysis.state,
            # Ground truth — blank
            "true_label":      "",
        }

        with self._lock:
            try:
                self._writer.writerow(row)
            except Exception as e:
                logger.error(f"SignalLogger write error: {e}")

    def close(self):
        with self._lock:
            if self._file:
                self._file.flush()
                self._file.close()
                self._file = None
        logger.info(f"SignalLogger closed → {self._filepath}")


def _r(val, digits=1):
    """Round float or return empty string for None."""
    if val is None:
        return ""
    try:
        return round(float(val), digits)
    except (TypeError, ValueError):
        return ""
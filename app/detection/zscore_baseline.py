"""
zscore_baseline.py — Per-person adaptive signal baseline tracker.

PROBLEM:
  A single threshold (e.g. HEAD_DROP_SLEEP=55°) applies to all 15 people.
  Person A naturally works with head tilted 45° (reading posture).
  Person B naturally sits bolt upright at 10°.
  The same threshold flags A as drowsy constantly and misses B until 55°.

SOLUTION — Online Z-score anomaly detection:
  Each person builds their own baseline during confirmed-awake periods:
    mean and std of each signal when they are clearly alert.
  Fatigue is detected as deviation from THEIR OWN normal, not a global value:
    z_score = (current_value - person_mean) / person_std
    drowsy   = z_score > Z_DROWSY_THRESHOLD   (2.0 std above their norm)
    sleeping = z_score > Z_SLEEP_THRESHOLD    (3.0 std above their norm)

BASELINE LEARNING:
  - Learning phase: first BASELINE_WARMUP_FRAMES frames of confirmed-awake
    activity are used to build the initial baseline (mean + std).
  - Online update: baseline updates slowly during awake periods using
    exponential moving average — adapts to posture shifts over a shift.
  - Freeze: baseline stops updating when state is drowsy/sleeping.
    This prevents a sleeping person from "teaching" their sleep posture
    as their normal baseline.

SIGNALS TRACKED (all from body_signals.py):
  head_drop_angle   — most important for this camera angle
  spine_angle       — torso tilt
  head_tilt_angle   — lateral lean
  shoulder_ear_ratio— vertical ear-shoulder gap
  wrist_activity    — hand movement rate

OUTPUT — ZScoreResult added to SleepAnalysis:
  z_scores:         dict of signal → z_score value
  z_drowsy:         bool — any signal > Z_DROWSY_THRESHOLD
  z_sleeping:       bool — any signal > Z_SLEEP_THRESHOLD
  baseline_ready:   bool — has enough data to make decisions
  samples_collected: int — how many awake frames in baseline

  Learning phase (~5 min per person):
The baseline only learns during frames where the person is wrist_active AND 
inactive < DROWSY_SECONDS AND not reclined — confirmed alert working posture. 
It collects 150 such frames using Welford's online algorithm (numerically stable 
running mean + variance). Until 150 awake frames are collected, z-score is disabled 
and existing signals carry the decision.
After warmup — detection:
Every frame computes z = (current_value − person_mean) / person_std for all 5 signals. 
The std has a floor (ZSCORE_MIN_STD=2.0°) so a person who sits perfectly still doesn't 
get a hair-trigger baseline. z > 2.0 → drowsy signal. z > 3.0 → sleep signal. 
Either one feeds into the existing multi-signal fusion alongside EAR/PERCLOS, 
head drop, and recline.
"""
import os
import math
import logging
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
_Z_DROWSY     = float(os.getenv("Z_DROWSY_THRESHOLD",  "2.0"))   # std devs above baseline
_Z_SLEEP      = float(os.getenv("Z_SLEEP_THRESHOLD",   "3.0"))   # std devs above baseline
_WARMUP       = int(os.getenv("ZSCORE_WARMUP_FRAMES",  "150"))   # ~5min at 0.5fps per person
_MIN_STD      = float(os.getenv("ZSCORE_MIN_STD",      "2.0"))   # floor std (degrees)
                                                                   # prevents over-sensitivity
                                                                   # when person is very still
_EMA_ALPHA    = float(os.getenv("ZSCORE_EMA_ALPHA",    "0.02"))  # slow baseline drift rate

# Signals to track and their minimum std floors (prevents hair-trigger sensitivity)
# Floor = the smallest meaningful variation we expect for that signal
_SIGNAL_CONFIG = {
    "head_drop_angle":    {"min_std": 3.0,  "weight": 1.0},
    "spine_angle":        {"min_std": 3.0,  "weight": 0.8},
    "head_tilt_angle":    {"min_std": 2.0,  "weight": 0.7},
    "shoulder_ear_ratio": {"min_std": 0.01, "weight": 0.5},
    "wrist_activity":     {"min_std": 0.002,"weight": 0.4},
}


@dataclass
class ZScoreResult:
    z_scores:          dict  = field(default_factory=dict)  # signal → z_score
    z_drowsy:          bool  = False   # any signal crossed drowsy threshold
    z_sleeping:        bool  = False   # any signal crossed sleep threshold
    baseline_ready:    bool  = False   # enough warmup data collected
    samples_collected: int   = 0
    triggered_signal:  str   = ""      # which signal triggered (for UI)
    max_z:             float = 0.0     # highest z-score across all signals

    def to_dict(self) -> dict:
        return {
            "z_scores":          {k: round(v, 2) for k, v in self.z_scores.items()},
            "z_drowsy":          self.z_drowsy,
            "z_sleeping":        self.z_sleeping,
            "baseline_ready":    self.baseline_ready,
            "samples_collected": self.samples_collected,
            "triggered_signal":  self.triggered_signal,
            "max_z":             round(self.max_z, 2),
        }


class PersonBaseline:
    """
    Maintains a running mean + std for each signal for ONE person.
    Updates only during confirmed-awake frames.
    """

    def __init__(self):
        # Warmup buffers — raw values collected before computing mean/std
        self._warmup: dict[str, list] = {k: [] for k in _SIGNAL_CONFIG}
        self._warmup_done = False

        # Online mean and variance (Welford's algorithm for numerical stability)
        self._n:    dict[str, int]   = {k: 0   for k in _SIGNAL_CONFIG}
        self._mean: dict[str, float] = {k: 0.0 for k in _SIGNAL_CONFIG}
        self._M2:   dict[str, float] = {k: 0.0 for k in _SIGNAL_CONFIG}

        # EMA-updated mean for slow drift tracking after warmup
        self._ema_mean: dict[str, Optional[float]] = {k: None for k in _SIGNAL_CONFIG}

        self.samples_collected = 0

    def _welford_update(self, key: str, value: float):
        """Online mean/variance update (Welford's method — numerically stable)."""
        self._n[key]  += 1
        n    = self._n[key]
        mean = self._mean[key]
        delta = value - mean
        self._mean[key] += delta / n
        delta2 = value - self._mean[key]
        self._M2[key]   += delta * delta2

    def _std(self, key: str) -> float:
        n = self._n[key]
        if n < 2:
            return _SIGNAL_CONFIG[key]["min_std"]
        variance = self._M2[key] / (n - 1)
        raw_std  = math.sqrt(max(0.0, variance))
        return max(raw_std, _SIGNAL_CONFIG[key]["min_std"])

    def update_awake(self, signals: dict):
        """
        Feed one frame of awake-period signals into the baseline.
        Should only be called when state is confirmed 'awake'.
        """
        for key in _SIGNAL_CONFIG:
            val = signals.get(key)
            if val is None:
                continue

            # Warmup phase — collect raw values
            if not self._warmup_done:
                self._warmup[key].append(val)
            else:
                # Post-warmup: Welford update for statistics
                self._welford_update(key, val)
                # EMA for slow drift tracking
                if self._ema_mean[key] is None:
                    self._ema_mean[key] = val
                else:
                    self._ema_mean[key] = (
                        _EMA_ALPHA * val + (1 - _EMA_ALPHA) * self._ema_mean[key]
                    )

        self.samples_collected += 1

        # Check if warmup is complete
        if not self._warmup_done:
            min_samples = min(len(v) for v in self._warmup.values()
                              if len(self._warmup[list(_SIGNAL_CONFIG.keys())[0]]) > 0)
            if self.samples_collected >= _WARMUP:
                self._finalise_warmup()

    def _finalise_warmup(self):
        """Convert warmup buffer to Welford statistics."""
        for key, vals in self._warmup.items():
            for v in vals:
                self._welford_update(key, v)
            if vals:
                self._ema_mean[key] = float(np.mean(vals))
        self._warmup_done = True
        logger.info(
            f"PersonBaseline: warmup complete — "
            f"{self.samples_collected} awake samples. "
            f"Baselines: " +
            ", ".join(f"{k}={self._mean[k]:.1f}±{self._std(k):.1f}"
                      for k in _SIGNAL_CONFIG if self._n[k] > 0)
        )

    @property
    def ready(self) -> bool:
        return self._warmup_done

    def compute_z_scores(self, signals: dict) -> ZScoreResult:
        """
        Compute z-score for each signal against this person's baseline.
        Returns ZScoreResult with per-signal z-scores and thresholded flags.
        """
        if not self.ready:
            return ZScoreResult(
                baseline_ready    = False,
                samples_collected = self.samples_collected,
            )

        z_scores       = {}
        max_z          = 0.0
        triggered_sig  = ""
        z_drowsy       = False
        z_sleeping     = False

        for key, cfg in _SIGNAL_CONFIG.items():
            val = signals.get(key)
            if val is None:
                continue

            # Use EMA mean for comparison if available (tracks slow drift)
            baseline_mean = (self._ema_mean[key]
                             if self._ema_mean[key] is not None
                             else self._mean[key])
            std           = self._std(key)

            z = (val - baseline_mean) / std
            z_scores[key] = round(z, 2)

            # Only positive z-scores matter — signals getting WORSE
            # (wrist_activity is inverted: low wrist = high z for wrist_idle)
            if key == "wrist_activity":
                # Low wrist activity = person stopped moving = positive signal
                z_effective = -z  # invert: below baseline wrist = concerning
            else:
                z_effective = z

            weighted_z = z_effective * cfg["weight"]

            if weighted_z > max_z:
                max_z         = weighted_z
                triggered_sig = key

            if weighted_z >= _Z_SLEEP:
                z_sleeping = True
                z_drowsy   = True
            elif weighted_z >= _Z_DROWSY:
                z_drowsy   = True

        return ZScoreResult(
            z_scores          = z_scores,
            z_drowsy          = z_drowsy,
            z_sleeping        = z_sleeping,
            baseline_ready    = True,
            samples_collected = self.samples_collected,
            triggered_signal  = triggered_sig,
            max_z             = max_z,
        )
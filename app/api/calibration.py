"""
Calibration API — collects labeled landmark samples from the live stream
and computes camera-specific thresholds for posture/fatigue detection.

Endpoints:
  POST /calibrate/sample       — store a labeled sample {label, signals}
  GET  /calibrate/samples      — get all stored samples
  POST /calibrate/compute      — compute thresholds from samples, write .env
  DELETE /calibrate/samples    — clear all samples
  GET  /calibrate/status       — current calibration state + sample counts
"""
import os
import json
import logging
import statistics
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger      = logging.getLogger(__name__)
cal_router  = APIRouter()

# In-memory sample store (keyed by label)
_SAMPLES: dict[str, list[dict]] = {
    "sitting":  [],
    "standing": [],
    "sleeping": [],
    "drowsy":   [],
    "awake":    [],
}

# Which .env file to write
_ENV_PATH = os.path.abspath(
    os.getenv("ENV_PATH", os.path.join(os.path.dirname(__file__), "../../.env"))
)


class CalibSample(BaseModel):
    label:   str              # "sitting"|"standing"|"sleeping"|"drowsy"|"awake"
    signals: dict             # from SleepAnalysis.signals + debug
    track_id: Optional[int]  = None


class CalibResult(BaseModel):
    thresholds: dict
    written_to_env: bool
    summary: str


@cal_router.post("/calibrate/sample")
def add_sample(sample: CalibSample):
    label = sample.label.lower()
    if label not in _SAMPLES:
        raise HTTPException(status_code=400, detail=f"Unknown label: {label}. Use: {list(_SAMPLES.keys())}")
    _SAMPLES[label].append(sample.signals)
    counts = {k: len(v) for k, v in _SAMPLES.items()}
    logger.info(f"Calibration sample: {label} → total {counts}")
    return {"ok": True, "counts": counts}


@cal_router.get("/calibrate/samples")
def get_samples():
    return {
        "counts": {k: len(v) for k, v in _SAMPLES.items()},
        "samples": _SAMPLES,
    }


@cal_router.delete("/calibrate/samples")
def clear_samples():
    for k in _SAMPLES:
        _SAMPLES[k] = []
    return {"ok": True, "message": "All calibration samples cleared."}


@cal_router.get("/calibrate/status")
def calibration_status():
    counts  = {k: len(v) for k, v in _SAMPLES.items()}
    ready   = all(counts[k] >= 5 for k in ["sitting", "standing"])
    return {
        "counts":       counts,
        "ready":        ready,
        "min_required": 5,
        "message": (
            "Ready to compute thresholds." if ready
            else "Collect at least 5 samples of each posture class."
        ),
    }


@cal_router.post("/calibrate/compute")
def compute_thresholds():
    """
    Compute camera-specific thresholds from collected samples.
    Uses percentile separation between classes to set decision boundaries.
    Writes results directly to .env.
    """
    counts = {k: len(v) for k, v in _SAMPLES.items()}
    if counts["sitting"] < 3 or counts["standing"] < 3:
        raise HTTPException(status_code=400, detail="Need at least 3 sitting + 3 standing samples first.")

    thresholds = {}
    notes      = []

    def vals(label, key):
        return [s[key] for s in _SAMPLES[label] if s.get(key) is not None]

    def boundary(a_vals, b_vals, default):
        """Find the midpoint between 75th pct of 'a' and 25th pct of 'b'."""
        if not a_vals or not b_vals:
            return default
        a75 = sorted(a_vals)[int(len(a_vals) * 0.75)]
        b25 = sorted(b_vals)[int(len(b_vals) * 0.25)]
        mid = (a75 + b25) / 2
        return round(mid, 3)

    # ── Posture: sitting vs standing ─────────────────────────────────
    sit_knee_x   = vals("sitting",  "knee_hip_x_gap")
    std_knee_x   = vals("standing", "knee_hip_x_gap")
    sit_knee_y   = vals("sitting",  "knee_hip_y_gap")
    std_knee_y   = vals("standing", "knee_hip_y_gap")
    sit_sh_hip   = vals("sitting",  "torso_compactness")
    std_sh_hip   = vals("standing", "torso_compactness")

    if sit_knee_x and std_knee_x:
        thresholds["POSTURE_SEATED_KNEE_X_GAP"] = boundary(
            sit_knee_x, std_knee_x, 0.06
        )
        notes.append(
            f"Seated knee X gap: sit={statistics.mean(sit_knee_x):.3f} "
            f"stand={statistics.mean(std_knee_x):.3f} "
            f"→ threshold={thresholds['POSTURE_SEATED_KNEE_X_GAP']}"
        )

    if sit_knee_y and std_knee_y:
        thresholds["POSTURE_STANDING_KNEE_Y_GAP"] = boundary(
            std_knee_y, sit_knee_y, 0.12
        )
        notes.append(
            f"Standing knee Y gap: stand={statistics.mean(std_knee_y):.3f} "
            f"sit={statistics.mean(sit_knee_y):.3f} "
            f"→ threshold={thresholds['POSTURE_STANDING_KNEE_Y_GAP']}"
        )

    if sit_sh_hip and std_sh_hip:
        thresholds["POSTURE_SIT_Y_RATIO"] = boundary(sit_sh_hip, std_sh_hip, 0.20)
        notes.append(
            f"Torso compactness: sit={statistics.mean(sit_sh_hip):.3f} "
            f"stand={statistics.mean(std_sh_hip):.3f} "
            f"→ threshold={thresholds['POSTURE_SIT_Y_RATIO']}"
        )

    # ── Fatigue: head drop angle thresholds ─────────────────────────
    awake_hd   = vals("awake",    "head_drop_angle")
    drowsy_hd  = vals("drowsy",   "head_drop_angle")
    sleep_hd   = vals("sleeping", "head_drop_angle")

    if awake_hd and drowsy_hd:
        thresholds["HEAD_DROP_DROWSY_DEG"] = boundary(awake_hd, drowsy_hd, 25.0)
        notes.append(
            f"Head drop drowsy: awake={statistics.mean(awake_hd):.1f}° "
            f"drowsy={statistics.mean(drowsy_hd):.1f}° "
            f"→ threshold={thresholds['HEAD_DROP_DROWSY_DEG']}°"
        )

    if drowsy_hd and sleep_hd:
        thresholds["HEAD_DROP_SLEEP_DEG"] = boundary(drowsy_hd, sleep_hd, 40.0)

    # ── Fatigue: spine angle thresholds ──────────────────────────────
    awake_sp   = vals("awake",    "spine_angle")
    drowsy_sp  = vals("drowsy",   "spine_angle")

    if awake_sp and drowsy_sp:
        thresholds["SPINE_DROWSY_DEG"] = boundary(awake_sp, drowsy_sp, 30.0)
        notes.append(
            f"Spine angle drowsy: awake={statistics.mean(awake_sp):.1f}° "
            f"drowsy={statistics.mean(drowsy_sp):.1f}° "
            f"→ threshold={thresholds['SPINE_DROWSY_DEG']}°"
        )

    # ── Write to .env ─────────────────────────────────────────────────
    written = _write_to_env(thresholds)

    summary = (
        f"Computed {len(thresholds)} thresholds from "
        f"{sum(counts.values())} samples.\n" +
        "\n".join(notes)
    )
    logger.info(f"Calibration complete:\n{summary}")

    return CalibResult(
        thresholds=thresholds,
        written_to_env=written,
        summary=summary,
    )


def _write_to_env(thresholds: dict) -> bool:
    """Update matching lines in .env, or append new ones."""
    try:
        if os.path.exists(_ENV_PATH):
            with open(_ENV_PATH) as f:
                lines = f.readlines()
        else:
            lines = []

        updated = set()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            matched  = False
            for key, val in thresholds.items():
                if stripped.startswith(key + "=") or stripped.startswith(f"# {key}"):
                    new_lines.append(f"{key}={val}\n")
                    updated.add(key)
                    matched = True
                    break
            if not matched:
                new_lines.append(line)

        # Append any keys not already in the file
        for key, val in thresholds.items():
            if key not in updated:
                new_lines.append(f"\n# Auto-calibrated\n{key}={val}\n")

        with open(_ENV_PATH, "w") as f:
            f.writelines(new_lines)

        logger.info(f"Wrote {len(thresholds)} thresholds to {_ENV_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to write .env: {e}")
        return False
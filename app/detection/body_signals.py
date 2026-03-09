"""
body_signals.py — Extracts ALL body geometry signals used by both the
fatigue detector AND the posture classifier. Single source of truth —
computed once per frame, used everywhere, stored in SleepAnalysis.signals
so the calibration tool can measure them live.

Fatigue signals:
  spine_angle        — torso tilt from vertical (degrees). Sleeping → large.
  head_drop_angle    — head drooping forward from ear→nose vector (degrees).
  head_tilt_angle    — lateral ear-line tilt (degrees). Head fallen sideways.
  shoulder_ear_ratio — ears relative to shoulders. Drowsy → smaller.
  wrist_activity     — wrist midpoint displacement frame-to-frame.

Posture signals (NEW — were computed locally in classifier, now exported):
  knee_hip_y_gap     — normalised Y distance knee→hip. Large = standing.
  knee_hip_x_gap     — normalised X distance knee→hip. Large = seated/forward.
  torso_compactness  — hip-shoulder Y gap. Small = seated/lying.
  sh_hip_y_gap       — same as torso_compactness (alias for classifier compat)
"""
import math
from typing import Optional

_NOSE        = 0
_L_EAR       = 7;  _R_EAR      = 8
_L_SHOULDER  = 11; _R_SHOULDER = 12
_L_HIP       = 23; _R_HIP      = 24
_L_KNEE      = 25; _R_KNEE     = 26
_L_ANKLE     = 27; _R_ANKLE    = 28
_L_WRIST     = 15; _R_WRIST    = 16


def _get(lms, idx, min_vis=0.25):
    lm = lms[idx]
    if lm.visibility < min_vis:
        return None
    return lm.x, lm.y


def _midpoint(a, b):
    if a is None and b is None: return None
    if a is None: return b
    if b is None: return a
    return ((a[0]+b[0])/2, (a[1]+b[1])/2)


def _angle_from_vertical(p1, p2) -> Optional[float]:
    if p1 is None or p2 is None: return None
    dx = p2[0] - p1[0]; dy = p2[1] - p1[1]
    if dx == 0 and dy == 0: return None
    return math.degrees(math.atan2(abs(dx), abs(dy)))


def _angle_from_horizontal(p1, p2) -> Optional[float]:
    if p1 is None or p2 is None: return None
    dx = p2[0] - p1[0]; dy = p2[1] - p1[1]
    return math.degrees(math.atan2(abs(dy), abs(dx) + 1e-6))


def _r(v, n=3):
    return round(v, n) if v is not None else None


def extract_body_signals(landmarks, prev_wrist_pos=None) -> dict:
    lms = landmarks.landmark

    nose    = _get(lms, _NOSE)
    l_ear   = _get(lms, _L_EAR);   r_ear  = _get(lms, _R_EAR)
    l_sh    = _get(lms, _L_SHOULDER); r_sh = _get(lms, _R_SHOULDER)
    l_hip   = _get(lms, _L_HIP);   r_hip  = _get(lms, _R_HIP)
    l_kn    = _get(lms, _L_KNEE);  r_kn   = _get(lms, _R_KNEE)
    l_wrist = _get(lms, _L_WRIST); r_wrist= _get(lms, _R_WRIST)

    ear_mid   = _midpoint(l_ear,   r_ear)
    sh_mid    = _midpoint(l_sh,    r_sh)
    hip_mid   = _midpoint(l_hip,   r_hip)
    knee_mid  = _midpoint(l_kn,    r_kn)
    wrist_mid = _midpoint(l_wrist, r_wrist)

    # ── Fatigue signals ───────────────────────────────────────────────
    spine_angle        = _angle_from_vertical(hip_mid, sh_mid)
    head_drop_angle    = _angle_from_vertical(ear_mid, nose)
    head_tilt_angle    = _angle_from_horizontal(l_ear, r_ear) if (l_ear and r_ear) else None
    shoulder_ear_ratio = (sh_mid[1] - ear_mid[1]) if (ear_mid and sh_mid) else None

    wrist_activity = None
    if wrist_mid and prev_wrist_pos:
        dx = wrist_mid[0] - prev_wrist_pos[0]
        dy = wrist_mid[1] - prev_wrist_pos[1]
        wrist_activity = math.sqrt(dx*dx + dy*dy)

    # ── Posture signals (NEW — exported so calibration can measure them) ──
    knee_hip_y_gap   = None   # large → knees far below hips → standing
    knee_hip_x_gap   = None   # large → knees forward of hips → seated
    torso_compactness= None   # hip-shoulder Y gap (small = seated/lying)

    if sh_mid and hip_mid:
        torso_compactness = abs(hip_mid[1] - sh_mid[1])

    if knee_mid and hip_mid:
        knee_hip_y_gap = abs(knee_mid[1] - hip_mid[1])
        knee_hip_x_gap = abs(knee_mid[0] - hip_mid[0])

    return {
        # Fatigue
        "spine_angle":        _r(spine_angle, 1),
        "head_drop_angle":    _r(head_drop_angle, 1),
        "head_tilt_angle":    _r(head_tilt_angle, 1),
        "shoulder_ear_ratio": _r(shoulder_ear_ratio, 3),
        "wrist_activity":     _r(wrist_activity, 4),
        # Posture
        "knee_hip_y_gap":     _r(knee_hip_y_gap, 3),
        "knee_hip_x_gap":     _r(knee_hip_x_gap, 3),
        "torso_compactness":  _r(torso_compactness, 3),
        "sh_hip_y_gap":       _r(torso_compactness, 3),  # alias
        # Pass-through for next frame delta
        "wrist_pos":          wrist_mid,
    }
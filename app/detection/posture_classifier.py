"""
Posture classifier for active (non-sleeping) states.
Camera-agnostic — uses normalised landmark ratios, not pixel values.
All thresholds configurable via env vars.

Classifies into: sitting | standing | walking | unknown

Logic (top-down CCTV geometry):
  WALKING  — significant motion score (person is moving)
  STANDING — pose visible, body Y-span is compact (standing person
             from above looks like a small vertical blob)
  SITTING  — pose visible, body compact but hip landmarks clearly
             present and close to shoulders in Y (seated compactness)
  UNKNOWN  — pose not detected or not enough landmarks
"""
import os

# Thresholds — all env-configurable
_WALK_MOTION   = float(os.getenv("POSTURE_WALK_MOTION_THRESHOLD",  "2.0"))
_SIT_Y_RATIO   = float(os.getenv("POSTURE_SIT_Y_RATIO",            "0.25"))  # hip-shoulder Y gap / frame
_STAND_Y_RATIO = float(os.getenv("POSTURE_STAND_Y_RATIO",          "0.15"))

_L_SHOULDER = 11
_R_SHOULDER = 12
_L_HIP      = 23
_R_HIP      = 24
_NOSE       = 0


def classify_posture(pose_landmarks, frame_h: int, frame_w: int,
                     motion_score: float) -> str:
    """
    Returns one of: "walking" | "standing" | "sitting" | "unknown"
    Only called when state is NOT sleeping/drowsy.
    """
    if pose_landmarks is None:
        return "unknown"

    from app.config import POSE_LANDMARK_MIN_VISIBILITY

    lms = pose_landmarks.landmark

    def get(idx):
        lm = lms[idx]
        if lm.visibility < POSE_LANDMARK_MIN_VISIBILITY:
            return None
        return lm.x, lm.y   # normalised 0-1

    # Walking: person is moving
    if motion_score > _WALK_MOTION:
        return "walking"

    # Need shoulders and hips for sitting vs standing
    l_sh = get(_L_SHOULDER)
    r_sh = get(_R_SHOULDER)
    l_hp = get(_L_HIP)
    r_hp = get(_R_HIP)

    shoulders = [p for p in [l_sh, r_sh] if p]
    hips      = [p for p in [l_hp, r_hp] if p]

    if not shoulders:
        return "unknown"

    if not hips:
        # Shoulders visible but hips not — likely standing, hips occluded
        return "standing"

    shoulder_y = sum(p[1] for p in shoulders) / len(shoulders)
    hip_y      = sum(p[1] for p in hips)      / len(hips)

    # In top-down view: seated person has hips very close to shoulders (Y gap small)
    # Standing person: hips further from shoulders
    y_gap = abs(hip_y - shoulder_y)   # normalised, 0-1

    if y_gap < _SIT_Y_RATIO:
        return "sitting"

    return "standing"
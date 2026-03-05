"""
Posture classifier — sitting | standing | walking | unknown

CAMERA GEOMETRY (side-mounted, ~35° downward angle):
  Seated person:
    • Hips and shoulders close in Y (desk conceals lower body)
    • Knees MAY be visible — they stick out FORWARD (larger X gap from hips)
    • Knee Y is close to hip Y (not far below) because person is bent at 90°
    • Ankles often visible for nearby seated people
    → Key signal: knee is FORWARD of hip (seated posture), not below

  Standing person:
    • Hips clearly below shoulders (large Y gap)
    • Knees directly below hips (small X gap, large Y gap from hip)
    • Full leg chain visible

  The OLD logic (knees_below_hips OR ankles_visible → standing) fails
  because seated people near a side camera have BOTH of those true.

NEW LOGIC:
  1. Compute knee-hip Y gap  (large → standing, small → could be seated)
  2. Compute knee-hip X gap  (large → seated/forward-bent, small → standing)
  3. Combine: seated = (knee_y close to hip_y) AND (knee_x far from hip_x)
              standing = knee_y far below hip_y AND knee_x close to hip_x
"""
from app.config import (
    POSTURE_WALK_MOTION_THRESHOLD,
    POSTURE_SIT_Y_RATIO,
    POSTURE_STAND_Y_RATIO,
    POSE_LANDMARK_MIN_VISIBILITY,
)

_L_SHOULDER = 11
_R_SHOULDER = 12
_L_HIP      = 23
_R_HIP      = 24
_L_KNEE     = 25
_R_KNEE     = 26
_L_ANKLE    = 27
_R_ANKLE    = 28

# Knee-to-hip X gap (normalised): above this → knees forward → sitting
_SEATED_KNEE_X_GAP   = 0.06   # env: POSTURE_SEATED_KNEE_X_GAP
# Knee-to-hip Y gap (normalised): above this → knees well below hips → standing
_STANDING_KNEE_Y_GAP = 0.12   # env: POSTURE_STANDING_KNEE_Y_GAP


def classify_posture(pose_landmarks,
                     frame_h: int, frame_w: int,
                     motion_score: float) -> str:
    import os
    seated_knee_x   = float(os.getenv("POSTURE_SEATED_KNEE_X_GAP",   str(_SEATED_KNEE_X_GAP)))
    standing_knee_y = float(os.getenv("POSTURE_STANDING_KNEE_Y_GAP", str(_STANDING_KNEE_Y_GAP)))

    if pose_landmarks is None:
        return "unknown"

    lms = pose_landmarks.landmark

    def get(idx):
        lm = lms[idx]
        if lm.visibility < POSE_LANDMARK_MIN_VISIBILITY:
            return None
        return lm.x, lm.y

    # Walking handled upstream via centroid tracking — motion_score=0 always here
    if motion_score > POSTURE_WALK_MOTION_THRESHOLD:
        return "walking"

    l_sh = get(_L_SHOULDER); r_sh = get(_R_SHOULDER)
    l_hp = get(_L_HIP);      r_hp = get(_R_HIP)
    l_kn = get(_L_KNEE);     r_kn = get(_R_KNEE)

    shoulders = [p for p in [l_sh, r_sh] if p]
    hips      = [p for p in [l_hp, r_hp] if p]
    knees     = [p for p in [l_kn, r_kn] if p]

    if not shoulders:
        return "unknown"

    if not hips:
        # Hips not visible — can't determine posture reliably on side cam
        return "unknown"

    shoulder_y = sum(p[1] for p in shoulders) / len(shoulders)
    hip_y      = sum(p[1] for p in hips)      / len(hips)
    hip_x      = sum(p[0] for p in hips)      / len(hips)
    sh_hip_y_gap = abs(hip_y - shoulder_y)

    # ── If we have knees: use the knee geometry ───────────────────────
    if knees:
        knee_y = sum(p[1] for p in knees) / len(knees)
        knee_x = sum(p[0] for p in knees) / len(knees)

        knee_hip_y_gap = abs(knee_y - hip_y)   # large → standing (knees far below)
        knee_hip_x_gap = abs(knee_x - hip_x)   # large → seated (knees forward)

        # Seated: knees are close in Y to hips BUT displaced in X (forward)
        knees_seated   = knee_hip_x_gap > seated_knee_x and knee_hip_y_gap < standing_knee_y
        # Standing: knees are clearly below hips in Y, minimal X offset
        knees_standing = knee_hip_y_gap >= standing_knee_y

        if knees_seated:
            return "sitting"
        if knees_standing:
            return "standing"
        # Ambiguous knee geometry — fall through to shoulder-hip gap

    # ── Fallback: shoulder-to-hip Y gap only ─────────────────────────
    # Tighter threshold than before — only call sitting when gap is small
    if sh_hip_y_gap < POSTURE_SIT_Y_RATIO:
        return "sitting"

    return "standing"
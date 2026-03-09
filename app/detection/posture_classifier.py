"""
Posture classifier — sitting | standing | walking | unknown

Uses pre-computed signals from body_signals.extract_body_signals().
Thresholds are camera-specific and set by the calibration tool.

PRIORITY FIX:
  Old logic checked knees_seated BEFORE knees_standing.
  From a top-angle camera a standing person can have BOTH:
    knee_hip_x_gap > seated_threshold  (knees appear forward in projection)
    knee_hip_y_gap >= standing_threshold (knees also below hips)
  The seated check fired first → wrong result.

  New logic: STANDING always beats SEATED when knee_y gap is large enough.
  The Y gap is the more reliable signal from an angled camera.
  Seated check only fires when Y gap is clearly small (person bent at 90°).
"""
import os
from app.config import (
    POSTURE_WALK_MOTION_THRESHOLD,
    POSTURE_SIT_Y_RATIO,
    POSE_LANDMARK_MIN_VISIBILITY,
)

_L_SHOULDER = 11; _R_SHOULDER = 12
_L_HIP      = 23; _R_HIP      = 24
_L_KNEE     = 25; _R_KNEE     = 26

_SEATED_KNEE_X_GAP   = float(os.getenv("POSTURE_SEATED_KNEE_X_GAP",   "0.06"))
_STANDING_KNEE_Y_GAP = float(os.getenv("POSTURE_STANDING_KNEE_Y_GAP", "0.12"))


def classify_posture(pose_landmarks,
                     frame_h: int, frame_w: int,
                     motion_score: float,
                     signals: dict | None = None) -> str:
    """
    signals: pre-computed dict from body_signals.extract_body_signals().
             If provided, uses cached values. If None, computes from landmarks.
    """
    if pose_landmarks is None:
        return "unknown"

    # Reload thresholds every call — picks up calibration changes without restart
    seated_knee_x   = float(os.getenv("POSTURE_SEATED_KNEE_X_GAP",   str(_SEATED_KNEE_X_GAP)))
    standing_knee_y = float(os.getenv("POSTURE_STANDING_KNEE_Y_GAP", str(_STANDING_KNEE_Y_GAP)))

    if motion_score > POSTURE_WALK_MOTION_THRESHOLD:
        return "walking"

    # Use pre-computed signals if available, else compute inline
    if signals:
        knee_hip_y_gap   = signals.get("knee_hip_y_gap")
        knee_hip_x_gap   = signals.get("knee_hip_x_gap")
        torso_compactness= signals.get("torso_compactness")
    else:
        # Fallback: compute directly from landmarks
        lms = pose_landmarks.landmark

        def get(idx):
            lm = lms[idx]
            return (lm.x, lm.y) if lm.visibility >= POSE_LANDMARK_MIN_VISIBILITY else None

        l_sh = get(_L_SHOULDER); r_sh = get(_R_SHOULDER)
        l_hp = get(_L_HIP);      r_hp = get(_R_HIP)
        l_kn = get(_L_KNEE);     r_kn = get(_R_KNEE)

        shoulders = [p for p in [l_sh, r_sh] if p]
        hips      = [p for p in [l_hp, r_hp] if p]
        knees     = [p for p in [l_kn, r_kn] if p]

        if not shoulders or not hips:
            return "unknown"

        sh_y  = sum(p[1] for p in shoulders) / len(shoulders)
        hip_y = sum(p[1] for p in hips)      / len(hips)
        hip_x = sum(p[0] for p in hips)      / len(hips)
        torso_compactness = abs(hip_y - sh_y)

        if knees:
            kn_y = sum(p[1] for p in knees) / len(knees)
            kn_x = sum(p[0] for p in knees) / len(knees)
            knee_hip_y_gap = abs(kn_y - hip_y)
            knee_hip_x_gap = abs(kn_x - hip_x)
        else:
            knee_hip_y_gap = knee_hip_x_gap = None

    # ── Decision: STANDING check FIRST (higher priority) ────────────
    #
    # Why standing beats seated:
    #   From a top-angle camera, a standing person has knees clearly
    #   BELOW hips (large Y gap). This is unambiguous regardless of any
    #   apparent X offset caused by camera perspective.
    #
    #   A seated person's knees cannot be far below their hips because
    #   the chair holds them at roughly hip height.

    if knee_hip_y_gap is not None:
        # Strong standing signal: knees well below hips
        if knee_hip_y_gap >= standing_knee_y:
            return "standing"

        # Now check seated: knees close in Y AND displaced in X (forward)
        if knee_hip_x_gap is not None:
            if knee_hip_x_gap > seated_knee_x and knee_hip_y_gap < standing_knee_y:
                return "sitting"

    # ── Fallback: shoulder-hip Y gap ────────────────────────────────
    if torso_compactness is not None:
        if torso_compactness < POSTURE_SIT_Y_RATIO:
            return "sitting"

    return "standing"
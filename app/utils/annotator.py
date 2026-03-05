import cv2
import numpy as np
from app.detection.sleep_pose_detector import SleepAnalysis

# Extended state map — includes inactive compound states
STATE_COLORS = {
    "sleeping":          (0,   0,   220),
    "drowsy":            (0,  140,  255),
    "sitting_inactive":  (180, 80,  220),
    "standing_inactive": (160, 60,  200),
    "inactive":          (180, 80,  220),
    "sitting":           (0,  180,  220),
    "standing":          (0,  200,   80),
    "walking":           (50, 220,  100),
    "awake":             (0,  200,   80),
    "no_person":         (80,  80,   80),
    "unknown":           (80,  80,   80),
}

_CONNECTIONS = [
    (11,12),(11,13),(13,15),(12,14),(14,16),
    (11,23),(12,24),(23,24),
    (23,25),(25,27),(24,26),(26,28),
    (0,11),(0,12),
]

_ID_PALETTE = [
    (255,200, 50),(50, 220,255),(50,255,150),(255, 80,150),
    (150,100,255),(255,160, 50),(80, 255,200),(200, 80,255),
]


def _id_color(track_id: int) -> tuple:
    return _ID_PALETTE[track_id % len(_ID_PALETTE)]


def _label(state: str) -> str:
    """Human-readable label for any state including compound ones."""
    return {
        "sitting_inactive":  "SITTING (IDLE)",
        "standing_inactive": "STANDING (IDLE)",
        "no_person":         "NO PERSON",
    }.get(state, state.upper())


def draw_person(out: np.ndarray,
                track_id: int,
                x1: int, y1: int, x2: int, y2: int,
                state: str,
                analysis: "SleepAnalysis | None" = None,
                pose_landmarks=None) -> np.ndarray:
    from app.config import POSE_LANDMARK_MIN_VISIBILITY

    color    = STATE_COLORS.get(state, (80, 80, 80))
    id_color = _id_color(track_id)
    h, w     = out.shape[:2]

    # ── Skeleton ──────────────────────────────────────────────────────
    if pose_landmarks is not None:
        lms = pose_landmarks.landmark
        pts = {}
        for idx, lm in enumerate(lms):
            if lm.visibility >= POSE_LANDMARK_MIN_VISIBILITY:
                pts[idx] = (int(lm.x * w), int(lm.y * h))
        for a, b in _CONNECTIONS:
            if a in pts and b in pts:
                cv2.line(out, pts[a], pts[b], color, 2, cv2.LINE_AA)
        for pt in pts.values():
            cv2.circle(out, pt, 4, (255, 255, 255), -1)
            cv2.circle(out, pt, 4, color, 1)

    # ── Bounding box ──────────────────────────────────────────────────
    cv2.rectangle(out, (x1, y1), (x2, y2), id_color, 2)

    # ── ID + state badge ──────────────────────────────────────────────
    label       = f"P{track_id} {_label(state)}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
    badge_y1    = max(0, y1 - th - 10)
    badge_y2    = max(th + 4, y1)
    badge_x2    = min(w, x1 + tw + 10)

    overlay = out.copy()
    cv2.rectangle(overlay, (x1, badge_y1), (badge_x2, badge_y2), id_color, -1)
    cv2.addWeighted(overlay, 0.55, out, 0.45, 0, out)
    cv2.putText(out, label, (x1 + 5, badge_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 0), 1, cv2.LINE_AA)

    # ── Inline metrics for alert states ──────────────────────────────
    if analysis and state in ("sleeping", "drowsy", "sitting_inactive", "standing_inactive"):
        metrics = (f"inactive:{analysis.inactive_seconds:.0f}s  "
                   f"recline:{analysis.reclined_ratio:.2f}")
        cv2.putText(out, metrics, (x1 + 4, y2 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.30,
                    color, 1, cv2.LINE_AA)

    return out


def draw_global_overlay(frame: np.ndarray,
                        person_states: dict,
                        camera_id: str = "") -> np.ndarray:
    out  = frame.copy()
    h, w = out.shape[:2]

    n_sleep = sum(1 for ps in person_states.values()
                  if ps.state == "sleeping")
    n_total = len(person_states)

    bar_color = (0, 0, 160) if n_sleep > 0 else (15, 15, 15)
    overlay   = out.copy()
    cv2.rectangle(overlay, (0, 0), (w, 30), bar_color, -1)
    cv2.addWeighted(overlay, 0.7, out, 0.3, 0, out)

    info = (f"● LIVE   {camera_id}   {w}x{h}"
            f"   {n_total} person{'s' if n_total != 1 else ''}")
    if n_sleep > 0:
        info += f"   WARNING: {n_sleep} SLEEPING"

    cv2.putText(out, info, (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (220, 220, 220), 1, cv2.LINE_AA)
    return out


def draw_overlay(frame, analysis, state, ear, pose_landmarks=None):
    """Legacy single-person overlay — kept for fallback."""
    out   = frame.copy()
    h, w  = out.shape[:2]
    color = STATE_COLORS.get(state, (80, 80, 80))

    if pose_landmarks is not None:
        from app.config import POSE_LANDMARK_MIN_VISIBILITY
        lms = pose_landmarks.landmark
        pts = {}
        for idx, lm in enumerate(lms):
            if lm.visibility >= POSE_LANDMARK_MIN_VISIBILITY:
                pts[idx] = (int(lm.x * w), int(lm.y * h))
        for a, b in _CONNECTIONS:
            if a in pts and b in pts:
                cv2.line(out, pts[a], pts[b], color, 2, cv2.LINE_AA)
        for pt in pts.values():
            cv2.circle(out, pt, 4, (255, 255, 255), -1)
            cv2.circle(out, pt, 4, color, 1)
        if len(pts) >= 2:
            xs = [p[0] for p in pts.values()]
            ys = [p[1] for p in pts.values()]
            cv2.rectangle(out,
                          (max(0, min(xs)-18), max(0, min(ys)-18)),
                          (min(w, max(xs)+18), min(h, max(ys)+18)),
                          color, 2)

    overlay = out.copy()
    cv2.rectangle(overlay, (0, 0), (w, 38), color, -1)
    cv2.addWeighted(overlay, 0.6, out, 0.4, 0, out)
    cv2.putText(out, _label(state), (12, 26),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(out, f"{analysis.confidence*100:.0f}%", (w-68, 26),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 1, cv2.LINE_AA)
    return out
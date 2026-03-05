import cv2
import numpy as np
from app.detection.sleep_pose_detector import SleepAnalysis

STATE_COLORS = {
    "sleeping":  (0,   0,   220),
    "drowsy":    (0,  140,  255),
    "inactive":  (180, 80,  220),
    "sitting":   (0,  180,  220),
    "standing":  (0,  200,   80),
    "walking":   (50, 220,  100),
    "awake":     (0,  200,   80),
    "no_person": (80,  80,   80),
    "unknown":   (80,  80,   80),
}

_CONNECTIONS = [
    (11,12),(11,13),(13,15),(12,14),(14,16),
    (11,23),(12,24),(23,24),
    (23,25),(25,27),(24,26),(26,28),
    (0,11),(0,12),
]


def draw_overlay(frame: np.ndarray,
                 analysis: SleepAnalysis,
                 state: str,
                 ear: float | None,
                 pose_landmarks=None) -> np.ndarray:
    out  = frame.copy()
    h, w = out.shape[:2]
    color = STATE_COLORS.get(state, (80, 80, 80))

    # ── Pose skeleton + bounding box ──────────────────────────────────────
    if pose_landmarks is not None:
        from app.config import POSE_LANDMARK_MIN_VISIBILITY
        lms = pose_landmarks.landmark
        pts = {}
        for idx, lm in enumerate(lms):
            if lm.visibility >= POSE_LANDMARK_MIN_VISIBILITY:
                pts[idx] = (int(lm.x * w), int(lm.y * h))

        # Draw connections
        for a, b in _CONNECTIONS:
            if a in pts and b in pts:
                cv2.line(out, pts[a], pts[b], color, 2, cv2.LINE_AA)

        # Draw joints
        for pt in pts.values():
            cv2.circle(out, pt, 4, (255, 255, 255), -1)
            cv2.circle(out, pt, 4, color, 1)

        # Bounding box — use ALL visible points, not just connected ones
        if len(pts) >= 2:
            xs = [p[0] for p in pts.values()]
            ys = [p[1] for p in pts.values()]
            pad = 18
            x1 = max(0, min(xs) - pad)
            y1 = max(0, min(ys) - pad)
            x2 = min(w, max(xs) + pad)
            y2 = min(h, max(ys) + pad)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            # Label above box (or below if box is at top)
            label_y = y1 - 8 if y1 > 20 else y2 + 16
            cv2.putText(out, "PERSON", (x1 + 4, label_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                        color, 1, cv2.LINE_AA)

    # ── Top state banner ─────────────────────────────────────────────────
    banner_h = 38
    overlay = out.copy()
    cv2.rectangle(overlay, (0, 0), (w, banner_h), color, -1)
    cv2.addWeighted(overlay, 0.6, out, 0.4, 0, out)

    cv2.putText(out, state.upper(), (12, 26),
                cv2.FONT_HERSHEY_DUPLEX, 0.85,
                (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(out, f"{analysis.confidence*100:.0f}%", (w - 68, 26),
                cv2.FONT_HERSHEY_DUPLEX, 0.75,
                (255, 255, 255), 1, cv2.LINE_AA)

    # ── Metrics panel bottom-left ─────────────────────────────────────────
    panel_x, panel_y = 10, h - 110
    panel_w, panel_h_px = 220, 95
    roi  = out[panel_y:panel_y+panel_h_px, panel_x:panel_x+panel_w]
    dark = (roi.astype(np.float32) * 0.4).astype(np.uint8)
    out[panel_y:panel_y+panel_h_px, panel_x:panel_x+panel_w] = dark

    def bar(lbl, val, maxv, y_off, bc):
        pct  = min(1.0, val / maxv) if maxv > 0 else 0
        bx   = panel_x + 10
        by   = panel_y + y_off
        full = panel_w - 20
        cv2.putText(out, f"{lbl}: {val:.1f}", (bx, by - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (200, 200, 200), 1, cv2.LINE_AA)
        cv2.rectangle(out, (bx, by), (bx+full, by+5), (50,50,50), -1)
        if int(full*pct) > 0:
            cv2.rectangle(out, (bx, by), (bx+int(full*pct), by+5), bc, -1)

    bar("Inactive", analysis.inactive_seconds, 30,  18, color)
    bar("Reclined", analysis.reclined_ratio,    1.0, 40, color)
    bar("Motion",   analysis.motion_score,      10,  62, (100, 200, 255))
    if ear is not None:
        bar("EAR",  ear, 0.4, 84, (180, 180, 60))

    # ── Pose indicator ───────────────────────────────────────────────────
    dot = (0, 200, 80) if analysis.pose_visible else (80, 80, 80)
    cv2.circle(out, (w - 18, 52), 6, dot, -1)
    cv2.putText(out, "POSE", (w - 52, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, dot, 1, cv2.LINE_AA)

    return out
import cv2
import numpy as np
from app.detection.sleep_pose_detector import SleepAnalysis

# State → colour (BGR)
STATE_COLORS = {
    "sleeping":  (0,   0,   255),   # red
    "drowsy":    (0,  140,  255),   # orange
    "inactive":  (200, 100, 255),   # purple
    "awake":     (0,  230,  100),   # green
    "no_person": (100, 100, 100),   # grey
    "unknown":   (100, 100, 100),
}

def draw_overlay(frame: np.ndarray, analysis: SleepAnalysis,
                 state: str, ear: float | None) -> np.ndarray:
    """
    Draw detection overlay on frame and return annotated copy.
    Draws:
      - Coloured state banner across the top
      - Metric bars on the left
      - Pose skeleton landmarks (if visible)
    """
    out   = frame.copy()
    h, w  = out.shape[:2]
    color = STATE_COLORS.get(state, (100, 100, 100))

    # ── Top banner ────────────────────────────────────────────────────────
    banner_h = 38
    cv2.rectangle(out, (0, 0), (w, banner_h), color, -1)
    cv2.addWeighted(out, 0.75, frame, 0.25, 0, out)   # slight transparency

    # Reapply banner solid
    overlay = out.copy()
    cv2.rectangle(overlay, (0, 0), (w, banner_h), color, -1)
    cv2.addWeighted(overlay, 0.55, out, 0.45, 0, out)

    label = state.upper()
    conf  = f"{analysis.confidence*100:.0f}%"
    cv2.putText(out, label, (12, 26),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(out, conf, (w - 70, 26),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 1, cv2.LINE_AA)

    # ── Metrics panel (bottom-left) ───────────────────────────────────────
    panel_x, panel_y = 10, h - 110
    panel_w, panel_h = 220, 95
    panel = out[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w].copy()
    black = np.zeros_like(panel)
    cv2.addWeighted(black, 0.55, panel, 0.45, 0, panel)
    out[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w] = panel

    def metric_bar(label, value, max_val, y, bar_color):
        pct  = min(1.0, value / max_val) if max_val > 0 else 0
        bar_full_w = panel_w - 20
        bar_filled = int(bar_full_w * pct)
        bx = panel_x + 10
        by = panel_y + y
        # label + value
        cv2.putText(out, f"{label}: {value:.1f}", (bx, by - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)
        # background bar
        cv2.rectangle(out, (bx, by), (bx + bar_full_w, by + 5), (60, 60, 60), -1)
        # filled bar
        if bar_filled > 0:
            cv2.rectangle(out, (bx, by), (bx + bar_filled, by + 5), bar_color, -1)

    metric_bar("Inactive",  analysis.inactive_seconds, 30,  18, color)
    metric_bar("Reclined",  analysis.reclined_ratio,    1.0, 40, color)
    metric_bar("Motion",    analysis.motion_score,      10,  62, (100, 200, 255))
    if ear is not None:
        metric_bar("EAR",   ear,                        0.4, 84, (180, 180, 60))

    # ── Pose visibility indicator (top-right corner) ─────────────────────
    dot_color = (0, 230, 100) if analysis.pose_visible else (80, 80, 80)
    cv2.circle(out, (w - 18, 52), 6, dot_color, -1)
    cv2.putText(out, "POSE", (w - 52, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, dot_color, 1, cv2.LINE_AA)

    return out
from app.detection.posture_classifier import classify_posture


class StateAnalyzer:
    """
    Resolves final display state. Passes pre-computed signals to the
    posture classifier so knee geometry is never recomputed redundantly.
    """

    def analyze(self, pose_state: str, inactive: bool = False,
                pose_landmarks=None, frame_h: int = 480,
                frame_w: int = 640, motion_score: float = 0.0,
                signals: dict | None = None) -> str:

        if pose_state == "sleeping":  return "sleeping"
        if pose_state == "drowsy":    return "drowsy"
        if pose_state == "no_person": return "no_person"

        # Pass signals through so classifier uses cached knee geometry
        posture = classify_posture(
            pose_landmarks, frame_h, frame_w, motion_score,
            signals=signals
        )

        if posture in ("walking", "standing", "sitting"):
            return posture

        if inactive:
            return "inactive"

        if pose_state == "awake":
            return "awake"

        return pose_state
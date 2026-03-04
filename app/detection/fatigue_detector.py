from app.config import EAR_THRESHOLD
from app.detection.ear_calculator import compute_ear


class FatigueDetector:

    def __init__(self):

        self.threshold = EAR_THRESHOLD

    def check(self, left_eye, right_eye):

        left_ear = compute_ear(left_eye)
        right_ear = compute_ear(right_eye)

        ear = (left_ear + right_ear) / 2

        closed = ear < self.threshold

        return closed, ear
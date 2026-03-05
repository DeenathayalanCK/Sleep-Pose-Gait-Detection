import os
# Force MediaPipe to CPU-only — prevents EGL/GL crash in headless Docker
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

import mediapipe as mp
import logging

logger = logging.getLogger(__name__)


class PoseDetector:
    """Wraps MediaPipe Pose for full-body landmark detection."""

    def __init__(self):
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            # BUG FIX: original omitted min_tracking_confidence — MediaPipe
            # uses a default but being explicit avoids silent behaviour change.
            min_tracking_confidence=0.5,
        )

    def detect(self, rgb_frame):
        """Returns pose_landmarks or None."""
        result = self.pose.process(rgb_frame)
        return result.pose_landmarks
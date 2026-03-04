import mediapipe as mp

class PoseDetector:

    def __init__(self):

        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5
        )

    def detect(self, frame):

        result = self.pose.process(frame)

        return result.pose_landmarks
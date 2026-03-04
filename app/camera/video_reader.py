import cv2
from app.config import VIDEO_SOURCE

class VideoReader:

    def __init__(self):
        self.cap = cv2.VideoCapture(VIDEO_SOURCE)

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame
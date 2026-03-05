"""
YOLO + ByteTrack multi-person detector/tracker.

One call to .update(bgr_frame) returns a list of TrackedPerson objects
each containing: track_id, bbox (x1,y1,x2,y2), confidence.

All tuning parameters (model, conf, iou) come from config — nothing hardcoded.
"""
import logging
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TrackedPerson:
    track_id:   int
    x1: int; y1: int; x2: int; y2: int
    conf:       float

    @property
    def area(self) -> int:
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @property
    def center(self) -> tuple[int, int]:
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    def crop(self, frame: np.ndarray, pad: int = 20) -> np.ndarray:
        """Return padded crop of this person from the full frame."""
        h, w = frame.shape[:2]
        x1 = max(0, self.x1 - pad)
        y1 = max(0, self.y1 - pad)
        x2 = min(w, self.x2 + pad)
        y2 = min(h, self.y2 + pad)
        return frame[y1:y2, x1:x2]


class PersonTracker:
    """
    Wraps Ultralytics YOLOv8 + ByteTrack.
    Model is loaded once and reused across frames.
    """

    def __init__(self):
        from app.config import YOLO_MODEL, YOLO_CONF, YOLO_IOU
        from ultralytics import YOLO

        logger.info(f"Loading YOLO model: {YOLO_MODEL}")
        self._model    = YOLO(YOLO_MODEL)
        self._conf     = YOLO_CONF
        self._iou      = YOLO_IOU
        self._tracking = True
        logger.info("YOLO + ByteTrack ready.")

    def update(self, bgr_frame: np.ndarray) -> list[TrackedPerson]:
        """
        Run detection + tracking on one frame.
        Returns list of TrackedPerson, one per detected person.
        """
        results = self._model.track(
            bgr_frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],          # class 0 = person
            conf=self._conf,
            iou=self._iou,
            verbose=False,
        )

        persons = []
        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                # track_id can be None on first frame or if tracker loses lock
                tid = boxes.id[i] if boxes.id is not None else None
                if tid is None:
                    continue
                x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
                conf = float(boxes.conf[i])
                persons.append(TrackedPerson(
                    track_id=int(tid),
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    conf=conf,
                ))

        return persons
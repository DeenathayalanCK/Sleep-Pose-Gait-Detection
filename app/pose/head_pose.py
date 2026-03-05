import logging

logger = logging.getLogger(__name__)


class HeadNodDetector:
    """Detects a downward head nod from the Y position of the nose landmark."""

    # BUG FIX: original used a hard-coded pixel threshold of 15, which fires
    # constantly on minor jitter and is not normalised to frame resolution.
    # Now uses a normalised (0–1) coordinate threshold.
    NOD_THRESHOLD = 0.03  # ~3% of frame height

    def __init__(self):
        self.prev_y = None

    def detect(self, nose_y_normalised: float) -> bool:
        nod = False

        if self.prev_y is not None:
            diff = nose_y_normalised - self.prev_y
            if diff > self.NOD_THRESHOLD:
                nod = True

        self.prev_y = nose_y_normalised
        return nod

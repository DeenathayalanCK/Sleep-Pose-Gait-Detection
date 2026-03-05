import logging
from app.tracking.person_tracker import PersonTracker

logger = logging.getLogger(__name__)


class TrackManager:
    """
    Manages per-person state on top of PersonTracker bounding-box IDs.

    BUG FIX: track_manager.py was completely empty.  Without it there is
    no way to associate detection state (fatigue, pose) with a specific
    tracked person ID across frames.
    """

    def __init__(self):
        self.tracker   = PersonTracker()
        self._states: dict[int, dict] = {}

    def update(self, detections: list[tuple]) -> dict[int, dict]:
        """
        detections: list of (x1, y1, x2, y2) bounding boxes.
        Returns mapping of {person_id: state_dict}.
        """
        tracks = self.tracker.update(detections)

        # Prune stale IDs
        active_ids = set(tracks.keys())
        for tid in list(self._states.keys()):
            if tid not in active_ids:
                del self._states[tid]

        # Ensure every active track has a state entry
        for tid in active_ids:
            if tid not in self._states:
                self._states[tid] = {"state": "normal", "fatigue_duration": 0.0}

        return self._states

    def set_state(self, person_id: int, state: str, duration: float = 0.0):
        if person_id in self._states:
            self._states[person_id]["state"]            = state
            self._states[person_id]["fatigue_duration"] = duration

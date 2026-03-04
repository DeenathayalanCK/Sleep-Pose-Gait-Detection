import time
from app.config import FATIGUE_SECONDS

class FatigueEngine:

    def __init__(self):
        self.start_closed = None

    def update(self, closed):

        if closed:

            if self.start_closed is None:
                self.start_closed = time.time()

            duration = time.time() - self.start_closed

            if duration > FATIGUE_SECONDS:
                return True, duration

        else:
            self.start_closed = None

        return False, 0
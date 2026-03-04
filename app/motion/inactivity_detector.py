import time

class InactivityDetector:

    def __init__(self):

        self.last_move = time.time()
        self.prev_pos = None

    def update(self, position):

        now = time.time()

        if self.prev_pos is None:
            self.prev_pos = position
            return False

        dist = abs(position[0]-self.prev_pos[0]) + abs(position[1]-self.prev_pos[1])

        if dist > 5:
            self.last_move = now

        self.prev_pos = position

        if now - self.last_move > 20:
            return True

        return False
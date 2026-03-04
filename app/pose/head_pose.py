class HeadNodDetector:

    def __init__(self):
        self.prev_y=None

    def detect(self, nose_y):

        nod=False

        if self.prev_y is not None:

            diff = nose_y - self.prev_y

            if diff > 15:
                nod=True

        self.prev_y = nose_y

        return nod
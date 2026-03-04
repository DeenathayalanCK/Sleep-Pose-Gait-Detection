import cv2

class PersonTracker:

    def __init__(self):
        self.next_id = 0
        self.tracks = {}

    def update(self, detections):

        updated = {}

        for box in detections:

            x1,y1,x2,y2 = box
            cx = (x1+x2)//2
            cy = (y1+y2)//2

            assigned = False

            for tid,(tx,ty) in self.tracks.items():

                if abs(cx-tx)<50 and abs(cy-ty)<50:

                    updated[tid]=(cx,cy)
                    assigned=True
                    break

            if not assigned:

                updated[self.next_id]=(cx,cy)
                self.next_id+=1

        self.tracks = updated

        return self.tracks
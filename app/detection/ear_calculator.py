import numpy as np


def dist(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


def compute_ear(eye):

    A = dist(eye[1], eye[5])
    B = dist(eye[2], eye[4])
    C = dist(eye[0], eye[3])

    ear = (A + B) / (2.0 * C)

    return ear
import numpy as np


def euclidean(p1, p2) -> float:
    return float(np.linalg.norm(np.array(p1) - np.array(p2)))


def normalised_to_pixel(lm, w: int, h: int) -> tuple[int, int]:
    """Convert a MediaPipe normalised landmark to pixel coordinates."""
    return int(lm.x * w), int(lm.y * h)

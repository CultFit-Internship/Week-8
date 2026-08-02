"""
Vector math for joint angles.

calculate_angle(a, b, c) returns the angle at vertex b formed by
points a-b-c, using the cosine rule via the dot product.
"""

import numpy as np


def calculate_angle(a, b, c) -> float:
    """
    a, b, c: iterable of 2 or 3 coordinates, e.g. [x, y] or [x, y, z]
    Returns the angle at point b, in degrees (0-180).
    """
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    c = np.array(c, dtype=float)

    ba = a - b
    bc = c - b

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < 1e-6 or norm_bc < 1e-6:
        # Degenerate case: landmarks collapsed onto each other
        # (e.g. occluded joint). Return NaN so callers can skip the frame.
        return float("nan")

    cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.degrees(np.arccos(cosine_angle))

    return float(angle)

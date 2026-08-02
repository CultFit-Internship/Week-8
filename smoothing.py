"""
Smoothing for noisy pose-landmark data.

Raw landmark coordinates jitter frame to frame, which makes joint angles
jitter too and can trigger false reps. Two smoothers are provided:

- EMASmoother: exponential moving average, low latency, good default for
  real-time video.
- MovingAverageSmoother: fixed-window average, slightly smoother but adds
  more lag. Useful if EMA alone isn't enough.
"""

from collections import deque
import numpy as np


class EMASmoother:
    def __init__(self, alpha: float = 0.4):
        """
        alpha: smoothing factor in (0, 1]. Lower = smoother but laggier,
        higher = more responsive but noisier. 0.3-0.5 is a good starting range.
        """
        self.alpha = alpha
        self.state = {}

    def smooth(self, landmark_id, coord):
        coord = np.array(coord, dtype=float)
        if landmark_id not in self.state:
            self.state[landmark_id] = coord
        else:
            self.state[landmark_id] = (
                self.alpha * coord + (1 - self.alpha) * self.state[landmark_id]
            )
        return self.state[landmark_id]

    def reset(self):
        self.state = {}


class MovingAverageSmoother:
    def __init__(self, window: int = 5):
        self.window = window
        self.buffers = {}

    def smooth(self, landmark_id, coord):
        if landmark_id not in self.buffers:
            self.buffers[landmark_id] = deque(maxlen=self.window)
        self.buffers[landmark_id].append(coord)
        arr = np.array(self.buffers[landmark_id])
        return arr.mean(axis=0)

    def reset(self):
        self.buffers = {}


class AngleSmoother:
    """Simpler alternative: smooth the scalar angle itself instead of
    each landmark coordinate. Cheaper, and often just as effective."""

    def __init__(self, alpha: float = 0.4):
        self.alpha = alpha
        self.value = None

    def smooth(self, angle: float) -> float:
        if angle != angle:  # NaN check, skip degenerate frames
            return self.value if self.value is not None else angle
        if self.value is None:
            self.value = angle
        else:
            self.value = self.alpha * angle + (1 - self.alpha) * self.value
        return self.value

    def reset(self):
        self.value = None

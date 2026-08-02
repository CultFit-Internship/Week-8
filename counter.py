"""
State machine for rep detection, plus ExerciseSession which ties together
landmark smoothing, angle calculation, and rep counting for one exercise.
"""

from .angles import calculate_angle
from .smoothing import EMASmoother, AngleSmoother
from .exercises import EXERCISE_CONFIG


class RepCounter:
    """
    Two-state machine per side ("start" / "active").
    A rep counts on the start -> active transition (angle drops below
    active_threshold while previously in "start").
    A minimum-frame debounce guards against single-frame noise spikes
    that smoothing alone doesn't fully remove.
    """

    def __init__(self, exercise_type: str, min_frames_in_stage: int = 3):
        if exercise_type not in EXERCISE_CONFIG:
            raise ValueError(f"Unknown exercise type: {exercise_type}")
        self.exercise_type = exercise_type
        self.config = EXERCISE_CONFIG[exercise_type]
        self.start_threshold = self.config["start_threshold"]
        self.active_threshold = self.config["active_threshold"]
        self.min_frames_in_stage = min_frames_in_stage

        self.stage = "start"
        self.count = 0
        self._pending_stage = None
        self._pending_frames = 0

    def _try_transition(self, candidate_stage):
        """Require the candidate stage to hold for N consecutive frames
        before committing, to filter single-frame jitter."""
        if candidate_stage == self.stage:
            self._pending_stage = None
            self._pending_frames = 0
            return False

        if candidate_stage == self._pending_stage:
            self._pending_frames += 1
        else:
            self._pending_stage = candidate_stage
            self._pending_frames = 1

        if self._pending_frames >= self.min_frames_in_stage:
            self.stage = candidate_stage
            self._pending_stage = None
            self._pending_frames = 0
            return True
        return False

    def update(self, angle: float, form_ok: bool = True) -> dict:
        if angle == angle:  # not NaN
            if angle > self.start_threshold:
                self._try_transition("start")
            elif angle < self.active_threshold and self.stage == "start" and form_ok:
                if self._try_transition("active"):
                    self.count += 1

        return {
            "angle": round(angle, 1) if angle == angle else None,
            "stage": self.stage,
            "count": self.count,
        }

    def reset(self):
        self.stage = "start"
        self.count = 0
        self._pending_stage = None
        self._pending_frames = 0


class ExerciseSession:
    """
    Combines: pose landmarks -> smoothing -> angle calc -> rep counting,
    for a single exercise type. Auto-picks left/right side per frame based
    on landmark visibility if the caller doesn't pin one down.
    """

    def __init__(self, exercise_type: str, ema_alpha: float = 0.4):
        self.exercise_type = exercise_type
        self.config = EXERCISE_CONFIG[exercise_type]
        self.counter = RepCounter(exercise_type)
        self.coord_smoother = EMASmoother(alpha=ema_alpha)
        self.angle_smoother = AngleSmoother(alpha=ema_alpha)

    def set_exercise(self, exercise_type: str):
        self.exercise_type = exercise_type
        self.config = EXERCISE_CONFIG[exercise_type]
        self.counter = RepCounter(exercise_type)
        self.coord_smoother.reset()
        self.angle_smoother.reset()

    def reset(self):
        self.counter.reset()
        self.coord_smoother.reset()
        self.angle_smoother.reset()

    def _pick_side(self, landmarks, visibility, ids_by_side):
        """Pick whichever side (left/right) has higher average landmark
        visibility this frame."""
        best_side, best_score = "left", -1.0
        for side, ids in ids_by_side.items():
            vis = [visibility.get(i, 0.0) for i in ids]
            score = sum(vis) / len(vis)
            if score > best_score:
                best_side, best_score = side, score
        return best_side

    def process(self, landmarks: dict, visibility: dict = None) -> dict:
        """
        landmarks: {landmark_id: [x, y]} (or [x, y, z]) -- typically
                   normalized MediaPipe coordinates.
        visibility: {landmark_id: float 0-1}, optional, used to auto-pick
                    left/right side.
        """
        visibility = visibility or {}
        ids_by_side = self.config["mediapipe_ids"]
        side = self._pick_side(landmarks, visibility, ids_by_side)
        a_id, b_id, c_id = ids_by_side[side]

        try:
            a = self.coord_smoother.smooth(a_id, landmarks[a_id])
            b = self.coord_smoother.smooth(b_id, landmarks[b_id])
            c = self.coord_smoother.smooth(c_id, landmarks[c_id])
        except KeyError:
            return {"angle": None, "stage": self.counter.stage,
                    "count": self.counter.count, "exercise": self.exercise_type,
                    "side": side, "error": "missing landmarks"}

        raw_angle = calculate_angle(a, b, c)
        angle = self.angle_smoother.smooth(raw_angle)

        form_ok = True
        form_check = self.config.get("form_check")
        if form_check is not None:
            fa_id, fb_id, fc_id = form_check["mediapipe_ids"][side]
            if fa_id in landmarks and fb_id in landmarks and fc_id in landmarks:
                fa = self.coord_smoother.smooth(fa_id, landmarks[fa_id])
                fb = self.coord_smoother.smooth(fb_id, landmarks[fb_id])
                fc = self.coord_smoother.smooth(fc_id, landmarks[fc_id])
                body_angle = calculate_angle(fa, fb, fc)
                form_ok = (body_angle == body_angle) and body_angle >= form_check["min_angle"]

        result = self.counter.update(angle, form_ok=form_ok)
        result["exercise"] = self.exercise_type
        result["side"] = side
        result["form_ok"] = form_ok
        return result

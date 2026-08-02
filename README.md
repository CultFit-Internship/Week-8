# Week 8 — Form Analysis & Real-Time Feedback Engine

Extends the Week 6/7 pose-tracking pipeline with rule-based exercise form
checking, spoken feedback, and a color-coded skeleton overlay.

## What's new this week

- **Rule-based form checking** — at least 5 heuristic rules per exercise
  (bicep curl, squat, push-up), built from MediaPipe Pose landmarks
  (shoulder, elbow, wrist, hip, knee, ankle, nose).
- **Feedback API schema** — every `/pose` response now includes:
  ```json
  {
    "status": "ok" | "warning" | "error",
    "feedback_text": "Keep your back straight",
    "bad_joints": ["left_hip", "left_shoulder"],
    "severity": "ok" | "warn" | "error"
  }
  ```
- **Backend debouncing** — a `FeedbackDebouncer` holds a status for a few
  consecutive frames before it's shown, so the UI doesn't flicker between
  states frame to frame.
- **Voice feedback** — the mobile app speaks `feedback_text` aloud via
  `expo-speech`, with a minimum 3-second debounce so it doesn't repeat
  itself constantly.
- **Skeleton overlay** — joints listed in `bad_joints` are colored
  green/yellow/red on screen based on `severity`.

## Files

| File | What it does |
|---|---|
| `angles.py` | 3D joint angle calculation (unchanged from Week 7) |
| `smoothing.py` | EMA smoothing for landmark coordinates and angles (unchanged) |
| `exercises.py` | Exercise configs + the 5-rules-per-exercise form checker |
| `counter.py` | Rep counting state machine + form-rule evaluation + debouncing |
| `app.py` | Entry point — see note below |
| `useFormFeedback.js` | React Native hook: speaks feedback via `expo-speech`, 3s debounce |
| `SkeletonOverlay.js` | React Native component: draws the pose skeleton, color-codes flagged joints |

> **Note on `app.py`:** the actual Flask route wiring (`/pose/detect` or
> similar) lives in a separate routes file from earlier weeks. `app.py`
> here just re-exports `calculate_angle` — see that routes file for where
> `ExerciseSession.process()` gets called per frame.

## How form checking works

1. Each incoming frame's landmarks are smoothed (`EMASmoother`).
2. `exercises.check_form_rules()` runs the exercise-specific rules and
   returns the worst severity found, plus a combined feedback message.
3. If severity is `"error"`, the rep is **not** counted for that frame
   (bad form doesn't earn a rep) — mirrors how Week 7 gated push-up reps.
4. The raw result is passed through `FeedbackDebouncer` before being
   returned, so the on-screen status is stable across a few frames.

## Rule thresholds

The angle/position thresholds in `exercises.py` (e.g. `back_angle < 150`)
are starting estimates, not clinically validated numbers. Tune them
against your own demo footage if a rule fires too often or not enough.

## Deliverable

Demo video showing:
- Live rep counting continuing to work
- A form mistake being detected (joint turns red/yellow on the overlay)
- The corresponding feedback spoken aloud within ~3 seconds

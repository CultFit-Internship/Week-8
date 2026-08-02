# Rep Counter Backend

Webcam-based rep counter for bicep curls, squats, and push-ups. Runs MediaPipe
Pose on each frame, computes the joint angle for the selected exercise,
feeds it through a DOWN/UP (`start`/`active`) state machine, and streams the
annotated video with a live angle/stage/rep overlay to a browser page.

## Project layout

```
rep_counter_app/
├── app.py                  # FastAPI server: webcam capture, MJPEG stream, REST API
├── requirements.txt
├── static/
│   └── index.html           # minimal browser UI (video + exercise buttons)
└── rep_counter/
    ├── angles.py             # calculate_angle(a, b, c) — cosine rule via dot product
    ├── smoothing.py          # EMASmoother / MovingAverageSmoother / AngleSmoother
    ├── exercises.py           # per-exercise landmark triplets + thresholds
    └── counter.py             # RepCounter state machine + ExerciseSession
```

## Setup

Requires Python 3.9+ and a machine with a webcam attached (this uses OpenCV
to grab frames server-side, not the browser's camera).

```bash
cd rep_counter_app
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open **http://localhost:8000** in a browser. You'll see the live camera
feed with the pose skeleton drawn on it, a rep counter, current stage, and
live joint angle overlaid on the video. Buttons let you switch between
Bicep Curl / Squat / Push-Up, and a Reset button zeroes the count.

If your webcam isn't at index 0, edit the `camera_index` argument passed to
`capture_loop()` in `app.py` (or the call in `start_capture_thread`).

## API

| Method | Endpoint          | Description                                      |
|--------|-------------------|---------------------------------------------------|
| GET    | `/`               | Browser UI                                        |
| GET    | `/video_feed`     | MJPEG stream with skeleton + overlay burned in     |
| GET    | `/api/stats`      | Current `{angle, stage, count, exercise, side}`    |
| GET    | `/api/exercises`  | List of supported exercise keys                    |
| POST   | `/api/exercise`   | Body `{"exercise_type": "squat"}` — switch exercise |
| POST   | `/api/reset`      | Reset the rep count to 0                            |

## How it works

1. **Capture loop** (background thread) grabs a frame, runs MediaPipe Pose,
   gets 33 normalized landmarks + per-landmark visibility.
2. **Side selection** — for each frame, whichever side (left/right) has
   higher average landmark visibility is used, so the app keeps working if
   you turn slightly or one side is occluded.
3. **Smoothing** — landmark coordinates go through an EMA smoother
   (`alpha=0.4` by default) before the angle is computed, and the resulting
   angle is smoothed again. This kills most single-frame jitter.
4. **Angle** — `calculate_angle(a, b, c)` uses `arccos` of the normalized dot
   product between vectors `b->a` and `b->c` to get the angle at the middle
   joint (e.g. elbow for curls, knee for squats).
5. **State machine** — `RepCounter` tracks a `start`/`active` stage per
   exercise. A rep counts on the `start -> active` transition (angle drops
   below the exercise's `active_threshold`), and each stage change must hold
   for 3 consecutive frames before committing, to reject noise spikes.
6. **Push-up form check** — in addition to the elbow angle, the
   shoulder-hip-ankle angle is checked to stay near a straight line (>150°)
   so reps only count with a reasonably flat body, not just bent knees.
7. **Overlay + API** — every frame's `{angle, stage, count}` is written into
   shared state under a lock; `/video_feed` streams the annotated JPEG frames,
   `/api/stats` exposes the same numbers as JSON for any client (e.g. a
   separate mobile app) that wants to draw its own overlay instead.

## Tuning thresholds

Per-exercise thresholds live in `rep_counter/exercises.py`
(`start_threshold`, `active_threshold`, and the push-up `form_check.min_angle`).
The provided values are reasonable defaults but people's range of motion
varies — test on yourself and adjust.

## Mobile client note

The assignment mentions displaying the count as an overlay on a mobile
camera screen. This backend already burns the overlay into `/video_feed`
(works in any mobile browser via an `<img>`/`<video>` tag pointed at that
URL). If instead the phone should run its own camera + overlay (e.g. a
React Native or Swift app doing on-device pose detection), have the mobile
client send `{landmarks, visibility}` to a small `POST /api/frame` endpoint
using `ExerciseSession.process()` directly — the `rep_counter` package is
fully decoupled from OpenCV/webcam capture and works the same way given any
source of pose landmarks. Happy to add that endpoint and a sample mobile
overlay if you're going that route instead of the server-side webcam.

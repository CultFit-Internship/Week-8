"""
Rep Counter backend.

Captures the local webcam, runs MediaPipe Pose per frame, calculates the
relevant joint angle for the selected exercise, runs it through the
DOWN/UP state machine, and:
  - streams the annotated video (skeleton + live angle/stage/count overlay)
    over MJPEG at /video_feed
  - exposes the same numbers as JSON at /api/stats
  - lets the client switch exercise type / reset the counter via POST

Run with:
    pip install -r requirements.txt
    python app.py
Then open http://localhost:8000 in a browser (needs webcam permission if
running the browser-cam variant; this version uses the server's own
webcam via OpenCV, so just run it on a machine that has a camera attached).
"""

import threading
import time

import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel

from rep_counter import ExerciseSession, list_exercises, EXERCISE_CONFIG

app = FastAPI(title="Rep Counter API")

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

DEFAULT_EXERCISE = "bicep_curl"

# ---------------------------------------------------------------------------
# Shared state between the capture thread and the API/streaming endpoints
# ---------------------------------------------------------------------------

class SharedState:
    def __init__(self):
        self.lock = threading.Lock()
        self.session = ExerciseSession(DEFAULT_EXERCISE)
        self.latest_frame_jpeg = None
        self.latest_stats = {
            "angle": None, "stage": "start", "count": 0,
            "exercise": DEFAULT_EXERCISE, "side": "left", "form_ok": True,
        }
        self.running = True

    def set_exercise(self, exercise_type: str):
        with self.lock:
            self.session.set_exercise(exercise_type)

    def reset(self):
        with self.lock:
            self.session.reset()

    def get_stats(self):
        with self.lock:
            return dict(self.latest_stats)

    def get_frame(self):
        with self.lock:
            return self.latest_frame_jpeg


state = SharedState()


# ---------------------------------------------------------------------------
# Capture + inference loop (runs in a background thread)
# ---------------------------------------------------------------------------

def landmarks_to_dicts(pose_landmarks, frame_shape):
    """Convert MediaPipe normalized landmarks into the {id: [x,y]} /
    {id: visibility} dicts the rep_counter package expects."""
    coords, vis = {}, {}
    for idx, lm in enumerate(pose_landmarks.landmark):
        coords[idx] = [lm.x, lm.y]  # normalized coords; angle calc is scale-invariant
        vis[idx] = lm.visibility
    return coords, vis


def draw_overlay(frame, stats):
    h, w = frame.shape[:2]

    # Semi-transparent header bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 90), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

    exercise_label = EXERCISE_CONFIG[stats["exercise"]]["label"]
    stage = stats["stage"].upper()
    count = stats["count"]
    angle = stats["angle"]

    stage_color = (0, 200, 0) if stage == "ACTIVE" else (200, 200, 200)

    cv2.putText(frame, exercise_label, (15, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"REPS: {count}", (15, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    cv2.putText(frame, f"STAGE: {stage}", (250, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, stage_color, 2)
    if angle is not None:
        cv2.putText(frame, f"ANGLE: {angle:.1f}", (500, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    if not stats.get("form_ok", True):
        cv2.putText(frame, "FIX FORM", (w - 180, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    return frame


def capture_loop(camera_index: int = 0):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open webcam at index {camera_index}. "
            "Check that a camera is connected and not in use by another app."
        )

    with mp_pose.Pose(
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
        model_complexity=1,
    ) as pose:
        while state.running:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)  # mirror for a natural "selfie" view
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = pose.process(rgb)
            rgb.flags.writeable = True

            stats = state.get_stats()

            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2),
                )
                coords, vis = landmarks_to_dicts(results.pose_landmarks, frame.shape)
                with state.lock:
                    stats = state.session.process(coords, vis)
                    state.latest_stats = stats

            frame = draw_overlay(frame, stats)

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                with state.lock:
                    state.latest_frame_jpeg = buf.tobytes()

    cap.release()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class ExerciseRequest(BaseModel):
    exercise_type: str


@app.on_event("startup")
def start_capture_thread():
    t = threading.Thread(target=capture_loop, daemon=True)
    t.start()


@app.get("/api/stats")
def get_stats():
    return state.get_stats()


@app.get("/api/exercises")
def get_exercises():
    return {"exercises": list_exercises()}


@app.post("/api/exercise")
def set_exercise(req: ExerciseRequest):
    if req.exercise_type not in EXERCISE_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unknown exercise: {req.exercise_type}")
    state.set_exercise(req.exercise_type)
    return state.get_stats()


@app.post("/api/reset")
def reset_counter():
    state.reset()
    return state.get_stats()


def mjpeg_generator():
    boundary = b"--frame"
    while True:
        frame = state.get_frame()
        if frame is not None:
            yield (boundary + b"\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(1 / 30)


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

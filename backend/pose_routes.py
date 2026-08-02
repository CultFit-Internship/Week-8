"""
Week 6 backend addition: real pose-detection endpoint.

POST /pose/detect
    body: { "frame": "<base64 jpeg/png string>" }
    returns: 33 MediaPipe Pose landmarks (name, x, y, z, visibility)

Wire-up (in your main app.py, alongside the Week 5 frame_bp):

    from pose_routes import pose_bp
    app.register_blueprint(pose_bp)

Install requirements first:
    pip install mediapipe opencv-python
"""

import base64
import binascii

import cv2
import mediapipe as mp
import numpy as np
from flask import Blueprint, jsonify, request

pose_bp = Blueprint("pose_bp", __name__)

mp_pose = mp.solutions.pose

# MediaPipe's 33 landmark names, in the exact order the model outputs them.
LANDMARK_NAMES = [lm.name.lower() for lm in mp_pose.PoseLandmark]

# One Pose instance reused across requests — creating it per-request is slow.
# static_image_mode=True because each request is an independent frame, not
# part of a tracked video stream on the server side.
_pose_model = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=1,
    min_detection_confidence=0.5,
)


def _decode_base64_image(b64_string):
    """Decode a base64 string into an OpenCV (BGR) image, or None on failure."""
    try:
        # Strip a data URI prefix if the frontend ever sends one
        # (e.g. "data:image/jpeg;base64,....").
        if "," in b64_string and b64_string.strip().startswith("data:"):
            b64_string = b64_string.split(",", 1)[1]

        img_bytes = base64.b64decode(b64_string, validate=True)
        np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return image
    except (binascii.Error, ValueError):
        return None


@pose_bp.route("/pose/detect", methods=["POST"])
def detect_pose():
    payload = request.get_json(silent=True) or {}
    frame_b64 = payload.get("frame")

    if not frame_b64:
        return jsonify({"error": "Missing 'frame' (base64 image string) in request body"}), 400

    image = _decode_base64_image(frame_b64)
    if image is None:
        return jsonify({"error": "'frame' could not be decoded as an image"}), 400

    # MediaPipe expects RGB, OpenCV decodes as BGR.
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    height, width = image.shape[:2]

    results = _pose_model.process(image_rgb)

    if not results.pose_landmarks:
        # Graceful "no person detected" response — not an error.
        return jsonify({
            "detected": False,
            "message": "No person detected in frame",
            "landmarks": [],
        }), 200

    landmarks = []
    for idx, lm in enumerate(results.pose_landmarks.landmark):
        landmarks.append({
            "id": idx,
            "name": LANDMARK_NAMES[idx],
            # x/y come back normalized (0-1) relative to image width/height.
            "x": round(lm.x, 4),
            "y": round(lm.y, 4),
            # z is relative depth (roughly same scale as x), hips are origin.
            "z": round(lm.z, 4),
            "visibility": round(lm.visibility, 4),
        })

    return jsonify({
        "detected": True,
        "image_width": width,
        "image_height": height,
        "landmarks": landmarks,
    }), 200
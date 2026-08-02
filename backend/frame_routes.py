import base64
import binascii
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

frame_bp = Blueprint("frame_bp", __name__)

# Same 16-joint order used by SkeletonOverlay.js on the mobile side.
JOINT_NAMES = [
    "nose",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "chest",
    "pelvis",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "neck",
]

# Same placeholder fractional coordinates as the frontend fallback, so the
# response is visually consistent with what's already drawn locally.
DUMMY_KEYPOINTS = [
    {"x": 0.50, "y": 0.12}, {"x": 0.38, "y": 0.22}, {"x": 0.62, "y": 0.22},
    {"x": 0.30, "y": 0.34}, {"x": 0.70, "y": 0.34}, {"x": 0.25, "y": 0.46},
    {"x": 0.75, "y": 0.46}, {"x": 0.50, "y": 0.24}, {"x": 0.50, "y": 0.50},
    {"x": 0.42, "y": 0.50}, {"x": 0.58, "y": 0.50}, {"x": 0.40, "y": 0.68},
    {"x": 0.60, "y": 0.68}, {"x": 0.38, "y": 0.86}, {"x": 0.62, "y": 0.86},
    {"x": 0.50, "y": 0.18},
]


@frame_bp.route("/api/frame/analyze", methods=["POST"])
def analyze_frame():
    payload = request.get_json(silent=True) or {}
    frame_b64 = payload.get("frame")

    if not frame_b64:
        return jsonify({"error": "Missing 'frame' (base64 image string) in request body"}), 400

    # Validate that it's actually base64 and get a rough size, without
    # doing any real image processing yet — that's for a later week.
    try:
        decoded = base64.b64decode(frame_b64, validate=True)
        frame_bytes = len(decoded)
    except (binascii.Error, ValueError):
        return jsonify({"error": "'frame' is not valid base64"}), 400

    joints = [
        {"id": i, "name": name, **point, "confidence": 0.0}
        for i, (name, point) in enumerate(zip(JOINT_NAMES, DUMMY_KEYPOINTS))
    ]

    response = {
        "status": "ok",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "frame_size_bytes": frame_bytes,
        "facing": payload.get("facing", "unknown"),
        "pose": {
            "joints": joints,
            "note": "Dummy response — real pose estimation not yet implemented.",
        },
    }
    return jsonify(response), 200
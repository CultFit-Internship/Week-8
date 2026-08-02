"""
Exercise landmark triplets + configurable per-exercise angle thresholds.

Landmark indices follow MediaPipe Pose's 33-point model:
https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
"""

# MediaPipe Pose landmark indices used here
LM = {
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
}

EXERCISE_CONFIG = {
    "bicep_curl": {
        "label": "Bicep Curl",
        "joint_points": ("shoulder", "elbow", "wrist"),
        "mediapipe_ids": {
            "left": (LM["left_shoulder"], LM["left_elbow"], LM["left_wrist"]),
            "right": (LM["right_shoulder"], LM["right_elbow"], LM["right_wrist"]),
        },
        # "start" = arm extended (large angle), "active" = curled (small angle)
        "start_threshold": 160,   # angle must exceed this to (re)enter start
        "active_threshold": 40,   # angle must drop below this to count a rep
        "direction": "decreasing",  # rep counts when angle goes start -> low
        # secondary check to reject bad form (optional, None disables)
        "form_check": None,
    },
    "squat": {
        "label": "Squat",
        "joint_points": ("hip", "knee", "ankle"),
        "mediapipe_ids": {
            "left": (LM["left_hip"], LM["left_knee"], LM["left_ankle"]),
            "right": (LM["right_hip"], LM["right_knee"], LM["right_ankle"]),
        },
        # "start" = standing (large angle), "active" = squatted down (small angle)
        "start_threshold": 160,
        "active_threshold": 90,
        "direction": "decreasing",
        "form_check": None,
    },
    "push_up": {
        "label": "Push-Up",
        "joint_points": ("shoulder", "elbow", "wrist"),
        "mediapipe_ids": {
            "left": (LM["left_shoulder"], LM["left_elbow"], LM["left_wrist"]),
            "right": (LM["right_shoulder"], LM["right_elbow"], LM["right_wrist"]),
        },
        # "start" = arms extended / plank (large angle), "active" = chest low (small angle)
        "start_threshold": 160,
        "active_threshold": 90,
        "direction": "decreasing",
        # plank check: shoulder-hip-ankle should stay roughly straight (~180deg)
        "form_check": {
            "triplet": ("shoulder", "hip", "ankle"),
            "mediapipe_ids": {
                "left": (LM["left_shoulder"], LM["left_hip"], LM["left_ankle"]),
                "right": (LM["right_shoulder"], LM["right_hip"], LM["right_ankle"]),
            },
            "min_angle": 150,  # body must stay this straight to count the rep
        },
    },
}


def list_exercises():
    return list(EXERCISE_CONFIG.keys())

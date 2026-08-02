import React from 'react';
import Svg, { Circle, Line } from 'react-native-svg';

/**
 * SkeletonOverlay (Week 6 update)
 * --------------------------------
 * Draws a skeleton from MediaPipe Pose's 33 landmarks, returned live by the
 * backend's POST /pose/detect endpoint. Falls back to a hardcoded 16-point
 * placeholder (from Week 5) when no live landmarks are available yet.
 *
 * Landmarks below `visibilityThreshold` are skipped — MediaPipe marks a
 * landmark's visibility low when it's occluded or off-frame, and drawing it
 * anyway just shows a wrong/jittery joint.
 */

// MediaPipe Pose's 33 landmark names, in model output order.
export const MEDIAPIPE_LANDMARK_NAMES = [
  'nose', 'left_eye_inner', 'left_eye', 'left_eye_outer',
  'right_eye_inner', 'right_eye', 'right_eye_outer',
  'left_ear', 'right_ear', 'mouth_left', 'mouth_right',
  'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
  'left_wrist', 'right_wrist', 'left_pinky', 'right_pinky',
  'left_index', 'right_index', 'left_thumb', 'right_thumb',
  'left_hip', 'right_hip', 'left_knee', 'right_knee',
  'left_ankle', 'right_ankle', 'left_heel', 'right_heel',
  'left_foot_index', 'right_foot_index',
];

// Bone connections by landmark index (MediaPipe's standard pose skeleton).
const MEDIAPIPE_BONES = [
  [11, 12], // shoulders
  [11, 13], [13, 15], // left arm
  [12, 14], [14, 16], // right arm
  [11, 23], [12, 24], // torso sides
  [23, 24], // hips
  [23, 25], [25, 27], [27, 29], [29, 31], // left leg
  [24, 26], [26, 28], [28, 30], [30, 32], // right leg
  [0, 11], [0, 12], // nose to shoulders (rough neck)
];

// Week 5 placeholder — kept as a fallback so the overlay isn't blank before
// the first live response arrives.
export const PLACEHOLDER_JOINTS = [
  { id: 0, name: 'nose', x: 0.5, y: 0.12 },
  { id: 1, name: 'left_shoulder', x: 0.38, y: 0.22 },
  { id: 2, name: 'right_shoulder', x: 0.62, y: 0.22 },
  { id: 3, name: 'left_elbow', x: 0.3, y: 0.34 },
  { id: 4, name: 'right_elbow', x: 0.7, y: 0.34 },
  { id: 5, name: 'left_wrist', x: 0.25, y: 0.46 },
  { id: 6, name: 'right_wrist', x: 0.75, y: 0.46 },
  { id: 7, name: 'chest', x: 0.5, y: 0.24 },
  { id: 8, name: 'pelvis', x: 0.5, y: 0.5 },
  { id: 9, name: 'left_hip', x: 0.42, y: 0.5 },
  { id: 10, name: 'right_hip', x: 0.58, y: 0.5 },
  { id: 11, name: 'left_knee', x: 0.4, y: 0.68 },
  { id: 12, name: 'right_knee', x: 0.6, y: 0.68 },
  { id: 13, name: 'left_ankle', x: 0.38, y: 0.86 },
  { id: 14, name: 'right_ankle', x: 0.62, y: 0.86 },
  { id: 15, name: 'neck', x: 0.5, y: 0.18 },
];
const PLACEHOLDER_BONES = [
  [15, 0], [15, 7], [7, 1], [7, 2], [1, 3], [3, 5], [2, 4], [4, 6],
  [7, 8], [8, 9], [8, 10], [9, 11], [11, 13], [10, 12], [12, 14],
];

export default function SkeletonOverlay({
  width,
  height,
  landmarks, // live data from /pose/detect: [{ id, name, x, y, visibility }, ...]
  visibilityThreshold = 0.5,
  jointColor = '#00E5FF',
  boneColor = '#00E5FF',
  jointRadius = 5,
}) {
  if (!width || !height) return null;

  const usingLive = Array.isArray(landmarks) && landmarks.length > 0;
  const joints = usingLive ? landmarks : PLACEHOLDER_JOINTS;
  const bones = usingLive ? MEDIAPIPE_BONES : PLACEHOLDER_BONES;

  const byId = Object.fromEntries(joints.map((j) => [j.id, j]));
  const isVisible = (j) =>
    j && (j.visibility === undefined || j.visibility >= visibilityThreshold);

  return (
    <Svg
      width={width}
      height={height}
      style={{ position: 'absolute', top: 0, left: 0 }}
      pointerEvents="none"
    >
      {bones.map(([a, b], i) => {
        const jointA = byId[a];
        const jointB = byId[b];
        if (!isVisible(jointA) || !isVisible(jointB)) return null;
        return (
          <Line
            key={`bone-${i}`}
            x1={jointA.x * width}
            y1={jointA.y * height}
            x2={jointB.x * width}
            y2={jointB.y * height}
            stroke={boneColor}
            strokeWidth={3}
            strokeLinecap="round"
            opacity={0.85}
          />
        );
      })}
      {joints.filter(isVisible).map((j) => (
        <Circle
          key={`joint-${j.id}`}
          cx={j.x * width}
          cy={j.y * height}
          r={jointRadius}
          fill={jointColor}
          stroke="#ffffff"
          strokeWidth={1.5}
        />
      ))}
    </Svg>
  );
}

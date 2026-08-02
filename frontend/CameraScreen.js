import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  Alert,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as MediaLibrary from 'expo-media-library';
import { Ionicons } from '@expo/vector-icons';

import SkeletonOverlay from './SkeletonOverlay';
import axios from 'axios';

// Standalone Axios instance for this project. Point this at your ngrok URL.
const api = axios.create({ baseURL: 'https://your-ngrok-url.ngrok-free.app' });

const FRAME_ENDPOINT = '/api/frame/analyze'; // Week 5 — dummy response
const POSE_ENDPOINT = '/pose/detect';        // Week 6 — real MediaPipe pose

// How often to pull a frame and send it for live pose detection.
// Lower = smoother overlay but more network/server load. 500ms is a
// reasonable starting point over a phone connection + free-tier ngrok.
const LIVE_POLL_INTERVAL_MS = 500;

export default function CameraScreen() {
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [mediaPermission, requestMediaPermission] = MediaLibrary.usePermissions();

  const [facing, setFacing] = useState('back');
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [status, setStatus] = useState('idle'); // idle | capturing | sending | success | error
  const [lastResponse, setLastResponse] = useState(null);

  // Week 6 — live pose state
  const [isLive, setIsLive] = useState(false);
  const [liveLandmarks, setLiveLandmarks] = useState(null);
  const [personDetected, setPersonDetected] = useState(null); // null = no attempt yet

  const cameraRef = useRef(null);
  const liveIntervalRef = useRef(null);
  const isFetchingRef = useRef(false); // prevents overlapping requests

  // ---------- Permission flow ----------
  if (!cameraPermission || !mediaPermission) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#00E5FF" />
      </View>
    );
  }

  if (!cameraPermission.granted || !mediaPermission.granted) {
    return (
      <SafeAreaView style={styles.centered}>
        <Ionicons name="camera-outline" size={56} color="#888" />
        <Text style={styles.permissionTitle}>Camera & Media Access Needed</Text>
        <Text style={styles.permissionBody}>
          CultCoach uses your camera to capture workout frames for live form
          feedback, and saves clips to your library so you can review them
          later. We only use these while you're actively using this screen.
        </Text>
        <TouchableOpacity
          style={styles.permissionButton}
          onPress={async () => {
            const camResult = await requestCameraPermission();
            if (camResult.granted) {
              await requestMediaPermission();
            }
          }}
        >
          <Text style={styles.permissionButtonText}>Grant Access</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const toggleFacing = () => {
    setFacing((prev) => (prev === 'back' ? 'front' : 'back'));
  };

  const handleLayout = (e) => {
    const { width, height } = e.nativeEvent.layout;
    setContainerSize({ width, height });
  };

  // ---------- Week 5: single-shot capture -> dummy endpoint ----------
  const captureAndSend = useCallback(async () => {
    if (!cameraRef.current || status === 'capturing' || status === 'sending') return;
    try {
      setStatus('capturing');
      const photo = await cameraRef.current.takePictureAsync({
        base64: true,
        quality: 0.5,
        skipProcessing: true,
      });
      await MediaLibrary.saveToLibraryAsync(photo.uri);

      setStatus('sending');
      const response = await api.post(FRAME_ENDPOINT, {
        frame: photo.base64,
        format: 'jpeg',
        facing,
        timestamp: Date.now(),
      });

      setLastResponse(response.data);
      setStatus('success');
    } catch (err) {
      console.error('Frame capture/send failed:', err);
      setStatus('error');
      Alert.alert('Capture Failed', 'Could not send the frame to the backend.');
    } finally {
      setTimeout(() => setStatus('idle'), 1200);
    }
  }, [status, facing]);

  // ---------- Week 6: live pose polling -> /pose/detect ----------
  const fetchLivePose = useCallback(async () => {
    if (!cameraRef.current || isFetchingRef.current) return;
    isFetchingRef.current = true;
    try {
      const photo = await cameraRef.current.takePictureAsync({
        base64: true,
        quality: 0.3,       // lower quality — this runs frequently, keep payloads small
        skipProcessing: true,
      });

      const response = await api.post(POSE_ENDPOINT, { frame: photo.base64 });
      const data = response.data;

      if (data.detected) {
        setLiveLandmarks(data.landmarks);
        setPersonDetected(true);
      } else {
        setLiveLandmarks(null);
        setPersonDetected(false);
      }
    } catch (err) {
      // Don't spam alerts on every failed poll — just log it.
      console.warn('Live pose fetch failed:', err.message);
    } finally {
      isFetchingRef.current = false;
    }
  }, []);

  const toggleLive = () => {
    setIsLive((prev) => !prev);
  };

  useEffect(() => {
    if (isLive) {
      liveIntervalRef.current = setInterval(fetchLivePose, LIVE_POLL_INTERVAL_MS);
    } else {
      clearInterval(liveIntervalRef.current);
      liveIntervalRef.current = null;
      setLiveLandmarks(null);
      setPersonDetected(null);
    }
    return () => clearInterval(liveIntervalRef.current);
  }, [isLive, fetchLivePose]);

  const statusLabel = {
    idle: null,
    capturing: 'Capturing frame…',
    sending: 'Sending to server…',
    success: 'Frame sent ✓',
    error: 'Send failed',
  }[status];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.cameraWrapper} onLayout={handleLayout}>
        <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing={facing} />

        {/* Live 33-point MediaPipe skeleton when isLive is on, else Week 5 placeholder */}
        <SkeletonOverlay
          width={containerSize.width}
          height={containerSize.height}
          landmarks={isLive ? liveLandmarks : null}
        />

        {isLive && personDetected === false && (
          <View style={[styles.statusBanner, styles.statusBannerError, { top: 60 }]}>
            <Text style={styles.statusText}>No person detected</Text>
          </View>
        )}

        {statusLabel && (
          <View
            style={[
              styles.statusBanner,
              status === 'error' && styles.statusBannerError,
              status === 'success' && styles.statusBannerSuccess,
            ]}
          >
            {(status === 'capturing' || status === 'sending') && (
              <ActivityIndicator size="small" color="#fff" style={{ marginRight: 8 }} />
            )}
            <Text style={styles.statusText}>{statusLabel}</Text>
          </View>
        )}

        <View style={styles.topControls}>
          <TouchableOpacity
            style={[styles.iconButton, isLive && styles.iconButtonActive]}
            onPress={toggleLive}
          >
            <Ionicons name={isLive ? 'body' : 'body-outline'} size={24} color="#fff" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.iconButton} onPress={toggleFacing}>
            <Ionicons name="camera-reverse-outline" size={26} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.bottomControls}>
        <TouchableOpacity
          style={[
            styles.captureButton,
            (status === 'capturing' || status === 'sending') && styles.captureButtonDisabled,
          ]}
          onPress={captureAndSend}
          disabled={status === 'capturing' || status === 'sending'}
        >
          <View style={styles.captureButtonInner} />
        </TouchableOpacity>
        <Text style={styles.hintText}>
          {isLive ? 'Live pose ON — tap body icon to stop' : 'Tap body icon for live pose · Tap circle to capture a frame'}
        </Text>
      </View>

      {lastResponse ? (
        <View style={styles.debugPanel}>
          <Text style={styles.debugText} numberOfLines={2}>
            Last capture response: {JSON.stringify(lastResponse)}
          </Text>
        </View>
      ) : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  centered: {
    flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, backgroundColor: '#111',
  },
  permissionTitle: { color: '#fff', fontSize: 18, fontWeight: '600', marginTop: 16, textAlign: 'center' },
  permissionBody: { color: '#aaa', fontSize: 14, marginTop: 8, textAlign: 'center', lineHeight: 20 },
  permissionButton: { marginTop: 20, backgroundColor: '#00E5FF', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 24 },
  permissionButtonText: { color: '#000', fontWeight: '700', fontSize: 15 },
  cameraWrapper: { flex: 1, overflow: 'hidden' },
  topControls: { position: 'absolute', top: 16, right: 16, flexDirection: 'row', gap: 10 },
  iconButton: { backgroundColor: 'rgba(0,0,0,0.5)', padding: 10, borderRadius: 24 },
  iconButtonActive: { backgroundColor: 'rgba(0,229,255,0.6)' },
  statusBanner: {
    position: 'absolute', top: 16, left: 16, flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.6)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16,
  },
  statusBannerSuccess: { backgroundColor: 'rgba(0,150,80,0.75)' },
  statusBannerError: { backgroundColor: 'rgba(180,30,30,0.75)' },
  statusText: { color: '#fff', fontSize: 13, fontWeight: '500' },
  bottomControls: { minHeight: 110, justifyContent: 'center', alignItems: 'center', backgroundColor: '#000', paddingVertical: 12 },
  captureButton: { width: 74, height: 74, borderRadius: 37, borderWidth: 4, borderColor: '#fff', justifyContent: 'center', alignItems: 'center' },
  captureButtonDisabled: { opacity: 0.5 },
  captureButtonInner: { width: 58, height: 58, borderRadius: 29, backgroundColor: '#00E5FF' },
  hintText: { color: '#999', fontSize: 11, marginTop: 8, textAlign: 'center', paddingHorizontal: 20 },
  debugPanel: { position: 'absolute', bottom: 120, left: 12, right: 12, backgroundColor: 'rgba(0,0,0,0.6)', padding: 8, borderRadius: 8 },
  debugText: { color: '#0f0', fontSize: 11, fontFamily: 'monospace' },
});

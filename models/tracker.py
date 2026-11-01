# -*- coding: utf-8 -*-
import cv2
import numpy as np

MP_AVAILABLE = False
mp_face_mesh = None

try:
    import mediapipe.python.solutions.face_mesh as mp_face_mesh
    MP_AVAILABLE = True
except (ImportError, AttributeError):
    try:
        from mediapipe import solutions
        mp_face_mesh = solutions.face_mesh
        MP_AVAILABLE = True
    except (ImportError, AttributeError):
        MP_AVAILABLE = False


class EyeTrackerEngine:
    """Motor de visão computacional: captura, landmarks faciais, EAR e fotometria."""

    def __init__(self):
        self.cap = None
        self.face_mesh = None
        if MP_AVAILABLE and mp_face_mesh is not None:
            self.face_mesh = mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )

        self.telemetry = {
            "name": "Integrated Webcam (OpenCV)",
            "qualityRating": 95,
            "mic": "None",
            "speaker": "None",
            "fps": 30,
            "width": 640,
            "height": 480,
            "megapixels": "0.31 MP",
            "aspectRatio": "1.33",
            "bitrate": "10.5 MB/s",
            "colorsCount": 109358,
            "avgR": 138,
            "avgG": 140,
            "avgB": 137,
            "lightness": 54.51,
            "luminosity": 54.82,
            "brightness": 54.25,
            "hue": 90,
            "saturation": 1.25
        }
        self.current_rgb_frame = None

    def start_camera(self) -> bool:
        if not MP_AVAILABLE:
            return False
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.cap = None
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
        self.telemetry["width"] = w
        self.telemetry["height"] = h
        self.telemetry["megapixels"] = f"{(w * h) / 1_000_000:.2f} MP"
        self.telemetry["aspectRatio"] = f"{w / max(1, h):.2f}"
        self.telemetry["name"] = "USB / Integrated Webcam (OpenCV)"
        return True

    def stop_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def process_frame(self):
        """Retorna: (sucesso, frame_bgr_desenhado, ear_l, ear_r, direcao_olhar, olhos_detectados)"""
        if self.cap is None:
            return False, None, 0.0, 0.0, "CENTER", False

        ret, frame_bgr = self.cap.read()
        if not ret or frame_bgr is None:
            return False, None, 0.0, 0.0, "CENTER", False

        mirrored_bgr = cv2.flip(frame_bgr, 1)
        self.current_rgb_frame = cv2.cvtColor(mirrored_bgr, cv2.COLOR_BGR2RGB)
        raw_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(raw_rgb)
        h, w, _ = mirrored_bgr.shape

        if not results.multi_face_landmarks:
            return True, mirrored_bgr, 0.0, 0.0, "CENTER", False

        landmarks = results.multi_face_landmarks[0].landmark

        # Contorno dos olhos
        left_eye_idxs = [362, 385, 387, 263, 373, 380]
        right_eye_idxs = [33, 160, 158, 133, 153, 144]
        for eye_group in (left_eye_idxs, right_eye_idxs):
            pts = np.array([
                [int((1.0 - landmarks[i].x) * w), int(landmarks[i].y * h)]
                for i in eye_group
            ], np.int32)
            cv2.polylines(mirrored_bgr, [pts], isClosed=True, color=(128, 222, 74), thickness=2)

        # Íris
        for iris_idx in (468, 473):
            if iris_idx < len(landmarks):
                ix = int((1.0 - landmarks[iris_idx].x) * w)
                iy = int(landmarks[iris_idx].y * h)
                cv2.circle(mirrored_bgr, (ix, iy), 4, (21, 204, 250), -1)

        # Cálculo do Eye Aspect Ratio (EAR)
        ear_l_v = np.hypot(landmarks[386].x - landmarks[374].x, landmarks[386].y - landmarks[374].y)
        ear_l_h = np.hypot(landmarks[362].x - landmarks[263].x, landmarks[362].y - landmarks[263].y)
        ear_l = float(ear_l_v / (ear_l_h if ear_l_h > 1e-6 else 1.0))

        ear_r_v = np.hypot(landmarks[159].x - landmarks[145].x, landmarks[159].y - landmarks[145].y)
        ear_r_h = np.hypot(landmarks[33].x - landmarks[133].x, landmarks[33].y - landmarks[133].y)
        ear_r = float(ear_r_v / (ear_r_h if ear_r_h > 1e-6 else 1.0))

        # Posição da íris / Direção do olhar
        detected_dir = "CENTER"
        if len(landmarks) > 473:
            iris_r = landmarks[468]
            c_r_in, c_r_out = landmarks[133], landmarks[33]
            ratio_r = (iris_r.x - min(c_r_in.x, c_r_out.x)) / max(1e-6, abs(c_r_in.x - c_r_out.x))

            iris_l = landmarks[473]
            c_l_in, c_l_out = landmarks[362], landmarks[263]
            ratio_l = (iris_l.x - min(c_l_in.x, c_l_out.x)) / max(1e-6, abs(c_l_in.x - c_l_out.x))

            avg_gaze_ratio = (ratio_r + ratio_l) / 2.0
            if avg_gaze_ratio < 0.38:
                detected_dir = "RIGHT"
            elif avg_gaze_ratio > 0.62:
                detected_dir = "LEFT"

        return True, mirrored_bgr, ear_l, ear_r, detected_dir, True

    def generate_simulated_frame(self, light_level: int, is_blinking: bool):
        w, h = 320, 240
        light_scale = light_level / 55.0
        clamp_c = lambda v: int(min(255, max(0, round(v * light_scale))))

        img_bgr = np.zeros((h, w, 3), dtype=np.uint8)
        img_bgr[:] = (clamp_c(155), clamp_c(148), clamp_c(140))

        cx, cy = w // 2, h // 2 + 8
        cv2.ellipse(img_bgr, (cx, cy), (54, 66), 0, 0, 360, (clamp_c(150), clamp_c(175), clamp_c(215)), -1)

        for ex in (cx - 22, cx + 22):
            ey = cy - 8
            if is_blinking:
                cv2.line(img_bgr, (ex - 12, ey), (ex + 12, ey), (21, 204, 250), 3)
            else:
                cv2.ellipse(img_bgr, (ex, ey), (12, 6), 0, 0, 360, (clamp_c(245), clamp_c(245), clamp_c(245)), -1)
                cv2.circle(img_bgr, (ex, ey), 5, (43, 41, 30), -1)
            cv2.ellipse(img_bgr, (ex, ey), (13, 2 if is_blinking else 7), 0, 0, 360, (128, 222, 74), 1)

        self.current_rgb_frame = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        return img_bgr

    def calculate_photometrics(self, eyes_detected: bool):
        if self.current_rgb_frame is None:
            return
        sampled = self.current_rgb_frame[::4, ::4, :]
        avg_rgb = sampled.mean(axis=(0, 1))
        avg_r, avg_g, avg_b = int(round(avg_rgb[0])), int(round(avg_rgb[1])), int(round(avg_rgb[2]))

        r_n, g_n, b_n = avg_r / 255.0, avg_g / 255.0, avg_b / 255.0
        max_c, min_c = max(r_n, g_n, b_n), min(r_n, g_n, b_n)
        delta = max_c - min_c

        lightness = ((max_c + min_c) / 2.0) * 100.0
        luminosity = (0.2126 * r_n + 0.7152 * g_n + 0.0722 * b_n) * 100.0
        brightness = ((r_n + g_n + b_n) / 3.0) * 100.0

        hue = 0
        if delta != 0:
            if max_c == r_n:
                hue = ((g_n - b_n) / delta) % 6
            elif max_c == g_n:
                hue = (b_n - r_n) / delta + 2
            else:
                hue = (r_n - g_n) / delta + 4
            hue = int(round(hue * 60))
            if hue < 0:
                hue += 360

        saturation = 0.0 if delta == 0 else (delta / (1.0 - abs(2.0 * (lightness / 100.0) - 1.0))) * 100.0

        lum_score = 100.0
        if luminosity < 28:
            lum_score = max(5.0, (luminosity / 28.0) * 100.0)
        elif luminosity > 82:
            lum_score = max(25.0, 100.0 - ((luminosity - 82.0) / 18.0) * 75.0)

        fps_score = min(100.0, (self.telemetry["fps"] / 28.0) * 100.0)
        eye_score = 100.0 if eyes_detected else 25.0
        quality = int(round(0.50 * lum_score + 0.25 * fps_score + 0.25 * eye_score))

        flat_pixels = (
            (sampled[:, :, 0].astype(np.uint32) << 16) |
            (sampled[:, :, 1].astype(np.uint32) << 8) |
            sampled[:, :, 2].astype(np.uint32)
        )
        unique_colors = min(262144, int(np.unique(flat_pixels).size * 16))

        self.telemetry.update({
            "avgR": avg_r, "avgG": avg_g, "avgB": avg_b,
            "lightness": lightness, "luminosity": luminosity, "brightness": brightness,
            "hue": hue, "saturation": saturation,
            "qualityRating": min(100, max(0, quality)),
            "colorsCount": unique_colors
        })
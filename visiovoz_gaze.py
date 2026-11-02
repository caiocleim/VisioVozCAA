import cv2
import json
import os
import time
import numpy as np
import mediapipe as mp

# Landmarks MediaPipe para íris e cantos dos olhos
LEFT_IRIS = [474, 475, 476, 477]
LEFT_EYE_CORNERS = [33, 133]

class VisioVozGaze:
    def __init__(self, config_file="calibration_data.json", smoothing=0.3):
        """
        :param config_file: Arquivo para persistência dos pesos da calibração.
        :param smoothing: Fator de amortecimento (0.1 a 0.5) para suavizar tremores.
        """
        self.config_file = config_file
        self.smoothing = smoothing
        self.last_screen_pos = None

        self.model_x = None
        self.model_y = None
        self.screen_w = 1280
        self.screen_h = 720
        self.is_calibrated = False

        # Tenta carregar calibração salva previamente
        self.load_calibration()

    def extract_features(self, landmarks, frame_w, frame_h):
        """Normaliza a posição da íris em relação aos cantos do olho."""
        try:
            iris_pts = np.array([[landmarks[p].x * frame_w, landmarks[p].y * frame_h] for p in LEFT_IRIS])
            iris_center = iris_pts.mean(axis=0)

            c1 = np.array([landmarks[LEFT_EYE_CORNERS[0]].x * frame_w, landmarks[LEFT_EYE_CORNERS[0]].y * frame_h])
            c2 = np.array([landmarks[LEFT_EYE_CORNERS[1]].x * frame_w, landmarks[LEFT_EYE_CORNERS[1]].y * frame_h])

            eye_width = np.linalg.norm(c2 - c1)
            if eye_width < 1e-4:
                return None

            norm_x = (iris_center[0] - c1[0]) / eye_width
            norm_y = (iris_center[1] - c1[1]) / eye_width
            return float(norm_x), float(norm_y)
        except Exception:
            return None

    def fit_and_save(self, calib_samples, screen_w, screen_h):
        """
        Ajusta o modelo de regressão e salva os pesos em JSON.
        calib_samples: lista de dicionários [{"eye": (x, y), "screen": (sx, sy)}]
        """
        self.screen_w = screen_w
        self.screen_h = screen_h

        data = []
        for sample in calib_samples:
            ex, ey = sample["eye"]
            sx, sy = sample["screen"]
            data.append([ex, ey, sx, sy])

        data = np.array(data)
        X = np.column_stack([data[:, 0], data[:, 1], np.ones(len(data))])

        self.model_x, _, _, _ = np.linalg.lstsq(X, data[:, 2], rcond=None)
        self.model_y, _, _, _ = np.linalg.lstsq(X, data[:, 3], rcond=None)
        self.is_calibrated = True

        payload = {
            "screen_w": self.screen_w,
            "screen_h": self.screen_h,
            "model_x": self.model_x.tolist(),
            "model_y": self.model_y.tolist()
        }
        with open(self.config_file, "w") as f:
            json.dump(payload, f, indent=4)
        return True

    def load_calibration(self):
        """Carrega os dados salvos do JSON se existirem."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                self.screen_w = data["screen_w"]
                self.screen_h = data["screen_h"]
                self.model_x = np.array(data["model_x"])
                self.model_y = np.array(data["model_y"])
                self.is_calibrated = True
                return True
            except Exception:
                self.is_calibrated = False
        return False

    def predict_screen_coords(self, eye_features):
        """Converte vetor ocular em coordenadas de tela (x, y) com filtro de suavização."""
        if not self.is_calibrated or eye_features is None:
            return None

        feat = np.array([eye_features[0], eye_features[1], 1.0])
        raw_x = float(np.dot(feat, self.model_x))
        raw_y = float(np.dot(feat, self.model_y))

        # Restringe aos limites físicos da janela/tela
        raw_x = max(0, min(self.screen_w, raw_x))
        raw_y = max(0, min(self.screen_h, raw_y))

        # Filtro de suavização (Exponential Moving Average)
        if self.last_screen_pos is None:
            smooth_x, smooth_y = raw_x, raw_y
        else:
            prev_x, prev_y = self.last_screen_pos
            smooth_x = prev_x + self.smoothing * (raw_x - prev_x)
            smooth_y = prev_y + self.smoothing * (raw_y - prev_y)

        self.last_screen_pos = (smooth_x, smooth_y)
        return int(smooth_x), int(smooth_y)
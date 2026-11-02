import cv2
import time
import numpy as np
import mediapipe as mp
from visiovoz_gaze import VisioVozGaze

def run_calibration():
    # Defina a resolução da tela ou janela do VisioVoz
    SCREEN_W, SCREEN_H = 1280, 720
    HOLD_TIME = 2.0  # Tempo de fixação em segundos por ponto

    gaze = VisioVozGaze()
    
    # 5 pontos estratégicos para a interface de cartões do VisioVoz
    pad_x, pad_y = int(SCREEN_W * 0.12), int(SCREEN_H * 0.12)
    calib_points = [
        (SCREEN_W // 2, SCREEN_H // 2),        # Centro
        (pad_x, pad_y),                       # Topo Esquerdo
        (SCREEN_W - pad_x, pad_y),            # Topo Direito
        (pad_x, SCREEN_H - pad_y),            # Fundo Esquerdo
        (SCREEN_W - pad_x, SCREEN_H - pad_y)  # Fundo Direito
    ]

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True, # Crucial para capturar a íris
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )

    cap = cv2.VideoCapture(0)
    cv2.namedWindow("VisioVoz - Calibracao", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("VisioVoz - Calibracao", SCREEN_W, SCREEN_H)

    current_idx = 0
    point_timer = time.time()
    collected_samples = []
    final_calibration_data = []

    while cap.isOpened() and current_idx < len(calib_points):
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        canvas = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
        current_target = calib_points[current_idx]

        eye_feat = None
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            eye_feat = gaze.extract_features(landmarks, w, h)

        elapsed = time.time() - point_timer
        progress = min(elapsed / HOLD_TIME, 1.0)

        if eye_feat:
            collected_samples.append(eye_feat)

        # Interface visual de fixação
        cv2.circle(canvas, current_target, 28, (60, 60, 60), -1)
        cv2.circle(canvas, current_target, int(28 * progress), (0, 220, 100), -1)
        cv2.circle(canvas, current_target, 28, (255, 255, 255), 2)

        info = f"Fixe o olhar no ponto [{current_idx + 1}/{len(calib_points)}]"
        cv2.putText(canvas, info, (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        if elapsed >= HOLD_TIME:
            if len(collected_samples) >= 10:
                # Usa a mediana para descartar ruído de piscada
                median_eye = np.median(np.array(collected_samples), axis=0)
                final_calibration_data.append({
                    "eye": (float(median_eye[0]), float(median_eye[1])),
                    "screen": current_target
                })
                collected_samples.clear()
                current_idx += 1
                point_timer = time.time()
            else:
                collected_samples.clear()
                point_timer = time.time()

        cv2.imshow("VisioVoz - Calibracao", canvas)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    if len(final_calibration_data) == len(calib_points):
        gaze.fit_and_save(final_calibration_data, SCREEN_W, SCREEN_H)
        print("Calibração concluída e salva com sucesso em 'calibration_data.json'!")
    else:
        print("Calibração cancelada ou incompleta.")

if __name__ == "__main__":
    run_calibration()
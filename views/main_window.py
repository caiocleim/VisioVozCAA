# -*- coding: utf-8 -*-
import cv2
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QKeyEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QSlider, QFrame,
    QProgressBar
)

from views.widgets import SelectableCardWidget
from views.modals import WebcamInfoModal, CalibrationModal


class CAAOcularMainWindow(QMainWindow):
    keyPressed = pyqtSignal(QKeyEvent)
    keyReleased = pyqtSignal(QKeyEvent)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisioVozCAA")
        self.resize(1280, 780)
        self.setStyleSheet("QMainWindow { background-color: #edf2f7; }")

        self.webcam_modal = WebcamInfoModal(self)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header Superior
        header = QFrame()
        header.setStyleSheet("background-color: #0f172a; border-bottom: 1px solid #1e293b;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        logo_badge = QLabel("👁 VisioVozCAA")
        logo_badge.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.2); color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 6px;
            padding: 4px 10px; font-weight: bold; font-size: 12px;
        """)
        subtitle = QLabel("Rastreamento Ocular Mirror (Espelhado) & Detecção de Íris")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")

        header_layout.addWidget(logo_badge)
        header_layout.addSpacing(8)
        header_layout.addWidget(subtitle)
        header_layout.addStretch()

        self.btn_mode_sim = QPushButton("Simulação")
        self.btn_mode_cam = QPushButton("Webcam Real")
        for b in (self.btn_mode_sim, self.btn_mode_cam):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(self.btn_mode_sim)
        header_layout.addWidget(self.btn_mode_cam)

        dwell_box = QFrame()
        dwell_box.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 6px;")
        dwell_layout = QHBoxLayout(dwell_box)
        dwell_layout.setContentsMargins(8, 2, 8, 2)
        lbl_perm = QLabel("Permanência:")
        lbl_perm.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.dwell_slider = QSlider(Qt.Orientation.Horizontal)
        self.dwell_slider.setRange(600, 2200)
        self.dwell_slider.setSingleStep(100)
        self.dwell_slider.setValue(1000)
        self.dwell_slider.setFixedWidth(80)
        self.dwell_val_display = QLabel("1.0s")
        self.dwell_val_display.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 11px;")
        dwell_layout.addWidget(lbl_perm)
        dwell_layout.addWidget(self.dwell_slider)
        dwell_layout.addWidget(self.dwell_val_display)
        header_layout.addWidget(dwell_box)

        self.btn_webcam_info = QPushButton("Webcam Info (95%)")
        self.btn_webcam_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_webcam_info.setStyleSheet("""
            QPushButton {
                background-color: rgba(245, 158, 11, 0.2); color: #fcd34d;
                border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 6px;
                padding: 5px 10px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(245, 158, 11, 0.3); }
        """)
        header_layout.addWidget(self.btn_webcam_info)

        self.btn_calib = QPushButton("🎯 Calibrar")
        self.btn_calib.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calib.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155;
                border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        header_layout.addWidget(self.btn_calib)

        self.btn_mute = QPushButton("🔊 Voz Ativa")
        self.btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mute.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #34d399; border: 1px solid #334155;
                border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        header_layout.addWidget(self.btn_mute)

        self.btn_csv = QPushButton("📊 Exportar CSV")
        self.btn_csv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_csv.setStyleSheet("""
            QPushButton {
                background-color: #0284c7; color: #ffffff;
                border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        header_layout.addWidget(self.btn_csv)
        root_layout.addWidget(header)

        # Banner de Feedback
        feedback_bar = QFrame()
        feedback_bar.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e2e8f0;")
        fb_layout = QHBoxLayout(feedback_bar)
        fb_layout.setContentsMargins(20, 8, 20, 8)
        self.feedback_action_text = QLabel(
            "Status do Comando: Iniciando câmera espelhada... Rastreamento ocular assistivo pronto."
        )
        self.feedback_action_text.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: 800;")
        self.focus_item_counter = QLabel("Opção Atual: 1 / 8")
        self.focus_item_counter.setStyleSheet("""
            background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;
            border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 11px;
        """)
        fb_layout.addWidget(self.feedback_action_text)
        fb_layout.addStretch()
        fb_layout.addWidget(self.focus_item_counter)
        root_layout.addWidget(feedback_bar)

        # Corpo Principal
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Coluna Esquerda: Câmera e HUD
        sidebar = QFrame()
        sidebar.setFixedWidth(340)
        sidebar.setStyleSheet("background-color: #111827; color: #ffffff; border-right: 1px solid #1e293b;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 12, 14, 12)
        side_layout.setSpacing(8)

        status_row = QHBoxLayout()
        lbl_st = QLabel("STATUS DO OLHAR:")
        lbl_st.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        self.tracking_status_badge = QLabel("Iniciando Câmera...")
        self.tracking_status_badge.setStyleSheet("""
            background-color: rgba(245, 158, 11, 0.15); color: #fcd34d;
            border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 4px;
            padding: 2px 8px; font-size: 11px; font-weight: bold;
        """)
        status_row.addWidget(lbl_st)
        status_row.addStretch()
        status_row.addWidget(self.tracking_status_badge)
        side_layout.addLayout(status_row)

        self.video_label = QLabel()
        self.video_label.setFixedSize(312, 220)
        self.video_label.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 10px;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(self.video_label)

        ear_row = QHBoxLayout()
        self.badge_ear_l = QLabel("OE (Esq): 0.29")
        self.badge_ear_r = QLabel("OD (Dir): 0.29")
        self.gaze_direction_pill = QLabel("↔ Olhar: Centro")
        self.gaze_direction_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for lbl in (self.badge_ear_l, self.badge_ear_r):
            lbl.setStyleSheet("""
                background-color: #020617; color: #6ee7b7; border: 1px solid #059669;
                border-radius: 4px; padding: 3px 6px; font-family: Consolas, monospace; font-size: 10px;
            """)
        self.gaze_direction_pill.setStyleSheet("""
            background-color: #0f172a; color: #e2e8f0; border: 1px solid #334155;
            border-radius: 8px; padding: 3px 8px; font-size: 10px; font-weight: bold;
        """)
        ear_row.addWidget(self.badge_ear_l)
        ear_row.addWidget(self.gaze_direction_pill, stretch=1)
        ear_row.addWidget(self.badge_ear_r)
        side_layout.addLayout(ear_row)

        dwell_hdr = QHBoxLayout()
        lbl_dw = QLabel("Progresso de Seleção (2 Olhos)")
        lbl_dw.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.dwell_percent_label = QLabel("0%")
        self.dwell_percent_label.setStyleSheet("color: #fbbf24; font-family: Consolas; font-weight: bold; font-size: 11px;")
        dwell_hdr.addWidget(lbl_dw)
        dwell_hdr.addStretch()
        dwell_hdr.addWidget(self.dwell_percent_label)
        side_layout.addLayout(dwell_hdr)

        self.dwell_progress_bar = QProgressBar()
        self.dwell_progress_bar.setRange(0, 100)
        self.dwell_progress_bar.setValue(0)
        self.dwell_progress_bar.setTextVisible(False)
        self.dwell_progress_bar.setFixedHeight(10)
        self.dwell_progress_bar.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border: 1px solid #334155; border-radius: 5px; }
            QProgressBar::chunk { background-color: #f59e0b; border-radius: 4px; }
        """)
        side_layout.addWidget(self.dwell_progress_bar)

        # Telemetria Fotométrica Lateral
        telemetry_box = QFrame()
        telemetry_box.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px;")
        t_layout = QVBoxLayout(telemetry_box)
        t_layout.setContentsMargins(10, 8, 10, 8)
        t_layout.setSpacing(5)

        q_top = QHBoxLayout()
        q_lbl = QLabel("⚡ QUALITY RATING (0-100%)")
        q_lbl.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: bold;")
        self.quality_val_lbl = QLabel("95%")
        self.quality_val_lbl.setStyleSheet("color: #34d399; font-family: Consolas; font-size: 13px; font-weight: 900;")
        q_top.addWidget(q_lbl)
        q_top.addStretch()
        q_top.addWidget(self.quality_val_lbl)
        t_layout.addLayout(q_top)

        self.quality_bar = QProgressBar()
        self.quality_bar.setRange(0, 100)
        self.quality_bar.setValue(95)
        self.quality_bar.setTextVisible(False)
        self.quality_bar.setFixedHeight(8)
        self.quality_bar.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border-radius: 4px; }
            QProgressBar::chunk { background-color: #10b981; border-radius: 4px; }
        """)
        t_layout.addWidget(self.quality_bar)

        metrics_grid = QGridLayout()
        self.mini_lum = QLabel("Luminosity: 54.8%")
        self.mini_light = QLabel("Lightness: 53.9%")
        self.mini_bright = QLabel("Brightness: 54.4%")
        self.mini_fps = QLabel("FPS: 30")
        self.mini_bitrate = QLabel("Bitrate: 10.5 MB/s")
        self.mini_huesat = QLabel("Hue/Sat: 90° / 1.1%")
        for idx, m_lbl in enumerate([
            self.mini_lum, self.mini_light, self.mini_bright,
            self.mini_fps, self.mini_bitrate, self.mini_huesat
        ]):
            m_lbl.setStyleSheet("color: #cbd5e1; font-family: Consolas, monospace; font-size: 10px;")
            metrics_grid.addWidget(m_lbl, idx // 2, idx % 2)
        t_layout.addLayout(metrics_grid)

        self.sim_light_frame = QFrame()
        sim_l_layout = QVBoxLayout(self.sim_light_frame)
        sim_l_layout.setContentsMargins(0, 4, 0, 0)
        self.sim_light_label = QLabel("Iluminação de Teste: 55% (Ideal)")
        self.sim_light_label.setStyleSheet("color: #fcd34d; font-size: 10px; font-weight: bold;")
        self.sim_light_slider = QSlider(Qt.Orientation.Horizontal)
        self.sim_light_slider.setRange(5, 100)
        self.sim_light_slider.setValue(55)
        sim_l_layout.addWidget(self.sim_light_label)
        sim_l_layout.addWidget(self.sim_light_slider)
        self.sim_light_frame.setVisible(False)
        t_layout.addWidget(self.sim_light_frame)

        side_layout.addWidget(telemetry_box)
        side_layout.addStretch()

        # Botões de Teste Manual
        ctrl_lbl = QLabel("CONTROLES MANUAIS & ATALHOS")
        ctrl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        side_layout.addWidget(ctrl_lbl)

        manual_row1 = QHBoxLayout()
        self.btn_prev = QPushButton("[Q] Piscar Esq")
        self.btn_sel = QPushButton("[Espaço] Selecionar")
        self.btn_next = QPushButton("[E] Piscar Dir")
        self.btn_prev.setStyleSheet("background-color: #1e293b; color: #6ee7b7; padding: 6px; border-radius: 6px; font-weight: bold; font-size: 10px;")
        self.btn_sel.setStyleSheet("background-color: rgba(245, 158, 11, 0.25); color: #fcd34d; padding: 6px; border-radius: 6px; font-weight: bold; font-size: 10px;")
        self.btn_next.setStyleSheet("background-color: #1e293b; color: #fcd34d; padding: 6px; border-radius: 6px; font-weight: bold; font-size: 10px;")
        manual_row1.addWidget(self.btn_prev)
        manual_row1.addWidget(self.btn_sel)
        manual_row1.addWidget(self.btn_next)
        side_layout.addLayout(manual_row1)

        manual_row2 = QHBoxLayout()
        self.btn_tab_l = QPushButton("← Olhar Esq [A]")
        self.btn_tab_r = QPushButton("Olhar Dir [D] →")
        for b in (self.btn_tab_l, self.btn_tab_r):
            b.setStyleSheet("background-color: #1e293b; color: #cbd5e1; padding: 5px; border-radius: 6px; font-size: 10px;")
        manual_row2.addWidget(self.btn_tab_l)
        manual_row2.addWidget(self.btn_tab_r)
        side_layout.addLayout(manual_row2)
        body_layout.addWidget(sidebar)

        # Área Direita: Matriz de Cartões e Abas
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        tabs_row = QHBoxLayout()
        self.tab_buttons = []
        for idx, cat in enumerate(["1. Necessidades", "2. Conforto", "3. Bem-Estar"]):
            t_btn = QPushButton(cat)
            t_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tabs_row.addWidget(t_btn)
            self.tab_buttons.append(t_btn)

        tabs_row.addStretch()
        self.focus_title_lbl = QLabel("Foco Atual: Cartão #1")
        self.focus_title_lbl.setStyleSheet("""
            background-color: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
            border-radius: 10px; padding: 6px 12px; font-size: 12px; font-weight: bold;
        """)
        tabs_row.addWidget(self.focus_title_lbl)
        main_layout.addLayout(tabs_row)

        self.cards_grid_layout = QGridLayout()
        self.cards_grid_layout.setSpacing(14)
        self.card_widgets = []
        for i in range(6):
            card_w = SelectableCardWidget(index=i, is_action_button=False)
            self.cards_grid_layout.addWidget(card_w, i // 3, i % 3)
            self.card_widgets.append(card_w)
        main_layout.addLayout(self.cards_grid_layout, stretch=1)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(14)
        self.btn_caregiver = SelectableCardWidget(index=6, is_action_button=True, is_emergency=False)
        self.btn_caregiver.set_content("🔔 CHAMAR CUIDADOR", "Solicitar presença no quarto (Opção 7)")
        self.btn_caregiver.setFixedHeight(96)

        self.btn_emergency = SelectableCardWidget(index=7, is_action_button=True, is_emergency=True)
        self.btn_emergency.set_content("🚨 ALERTA DE EMERGÊNCIA", "Acionar socorro imediato (Opção 8)")
        self.btn_emergency.setFixedHeight(96)

        actions_row.addWidget(self.btn_caregiver)
        actions_row.addWidget(self.btn_emergency)
        self.card_widgets.extend([self.btn_caregiver, self.btn_emergency])
        main_layout.addLayout(actions_row)

        footer_bar = QFrame()
        footer_bar.setStyleSheet("background-color: #0f172a; border-radius: 10px;")
        f_layout = QHBoxLayout(footer_bar)
        f_layout.setContentsMargins(14, 8, 14, 8)
        shortcuts_lbl = QLabel(
            "Olhar Esquerda/Direita: Mudar Aba  |  Piscar Dir [E]: Próxima Opção (0→7)  |  "
            "Piscar Esq [Q]: Opção Anterior  |  Piscar 2 Olhos [Espaço]: Selecionar"
        )
        shortcuts_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        f_layout.addWidget(shortcuts_lbl)
        main_layout.addWidget(footer_bar)

        body_layout.addWidget(main_area, stretch=1)
        root_layout.addWidget(body_widget, stretch=1)

    def display_opencv_frame(self, bgr_img: np.ndarray):
        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(pix)

    def update_dwell_visuals(self, percent: float, focus_index: int):
        clamped = int(min(100, max(0, round(percent))))
        self.dwell_progress_bar.setValue(clamped)
        self.dwell_percent_label.setText(f"{clamped}%")
        for i, w in enumerate(self.card_widgets):
            w.set_dwell_progress(clamped if i == focus_index else 0)

    def update_telemetry_hud(self, telemetry: dict):
        q = telemetry["qualityRating"]
        self.btn_webcam_info.setText(f"Webcam Info ({q}%)")
        self.quality_val_lbl.setText(f"{q}%")
        self.quality_bar.setValue(q)
        self.mini_lum.setText(f"Luminosity: {telemetry['luminosity']:.1f}%")
        self.mini_light.setText(f"Lightness: {telemetry['lightness']:.1f}%")
        self.mini_bright.setText(f"Brightness: {telemetry['brightness']:.1f}%")
        self.mini_fps.setText(f"FPS: {telemetry['fps']}")
        self.mini_bitrate.setText(f"Bitrate: {telemetry['bitrate']}")
        self.mini_huesat.setText(f"Hue/Sat: {telemetry['hue']}° / {telemetry['saturation']:.1f}%")

        if self.webcam_modal.isVisible():
            self.webcam_modal.update_table(telemetry)

    def update_gaze_hud(self, direction: str):
        if direction == "LEFT":
            self.gaze_direction_pill.setText("← Olhando Esquerda (Aba ←)")
        elif direction == "RIGHT":
            self.gaze_direction_pill.setText("Olhando Direita (Aba →) →")
        else:
            self.gaze_direction_pill.setText("↔ Olhar: Centro")

    def keyPressEvent(self, event: QKeyEvent):
        if not event.isAutoRepeat():
            self.keyPressed.emit(event)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if not event.isAutoRepeat():
            self.keyReleased.emit(event)
        super().keyReleaseEvent(event)
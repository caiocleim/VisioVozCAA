from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView
)

import time
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar
)


class WebcamInfoModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Webcam Information")
        self.setFixedSize(440, 610)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; color: #0f172a; }
            QLabel#HeaderTitle { font-size: 14px; font-weight: bold; color: #1e293b; }
            QTableWidget {
                background-color: #ffffff; color: #1e293b;
                font-family: Consolas, monospace; font-size: 11.5px;
                border: 1px solid #cbd5e1; gridline-color: #e2e8f0;
            }
            QPushButton#CloseBtn {
                background-color: #1e293b; color: #ffffff;
                padding: 6px 16px; border-radius: 6px; font-weight: bold;
            }
            QPushButton#CloseBtn:hover { background-color: #334155; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setStyleSheet("background-color: #e8f4fc; border-bottom: 1px solid #cbd5e1;")
        header_layout = QHBoxLayout(header)
        title_lbl = QLabel("Webcam Information")
        title_lbl.setObjectName("HeaderTitle")
        header_layout.addWidget(title_lbl)
        layout.addWidget(header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        self.table = QTableWidget(21, 2)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        self.row_labels = [
            "Webcam Name:", "Quality Rating:", "Built-in Microphone:", "Built-in Speaker:",
            "Frame rate:", "Stream Type:", "Image Mode:", "Webcam MegaPixels:",
            "Webcam Resolution:", "Video Standard:", "Aspect Ratio:", "PNG File Size:",
            "JPEG File Size:", "Bitrate:", "Number of Colors:", "Average RGB Color:",
            "Lightness:", "Luminosity:", "Brightness:", "Hue:", "Saturation:"
        ]

        for row_idx, label in enumerate(self.row_labels):
            item_key = QTableWidgetItem(label)
            item_key.setForeground(QColor("#334155"))
            self.table.setItem(row_idx, 0, item_key)
            self.table.setItem(row_idx, 1, QTableWidgetItem("-"))
            self.table.setRowHeight(row_idx, 23)

        body_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Fechar")
        close_btn.setObjectName("CloseBtn")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        body_layout.addLayout(btn_row)

        layout.addWidget(body)

    def update_table(self, t: dict):
        values = [
            t["name"], f"{t['qualityRating']}% (0-100%)", t["mic"], t["speaker"],
            f"{t['fps']} FPS", "video", "rgb", t["megapixels"],
            f"{t['width']}×{t['height']}", "HD", t["aspectRatio"], "1.8 MB",
            "716.85 kB", t["bitrate"], str(t["colorsCount"]),
            f"rgb({t['avgR']}, {t['avgG']}, {t['avgB']})",
            f"{t['lightness']:.2f}%", f"{t['luminosity']:.2f}%",
            f"{t['brightness']:.2f}%", f"{t['hue']}°", f"{t['saturation']:.2f}%"
        ]
        for idx, val in enumerate(values):
            item = self.table.item(idx, 1)
            if item:
                item.setText(val)



    calibration_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibração Ocular - 5 Pontos")
        self.setModal(True)
        self.resize(900, 620)
        self.setStyleSheet("QDialog { background-color: #020617; color: #ffffff; }")

        self.calib_step = 0
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)

        badge = QLabel("CALIBRAÇÃO OCULAR")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("""
            background-color: rgba(245, 158, 11, 0.2);
            color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4);
            border-radius: 10px; padding: 4px 12px; font-weight: bold; font-size: 11px;
        """)
        title = QLabel("Clique ou olhe para cada ponto amarelo")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff; margin-top: 6px;")

        main_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        self.canvas_frame = QFrame()
        self.canvas_frame.setStyleSheet("""
            QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; }
        """)
        grid = QGridLayout(self.canvas_frame)
        grid.setContentsMargins(32, 32, 32, 32)

        self.point_buttons = []
        positions = [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)]
        for i, (r, c) in enumerate(positions):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(52, 52)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #facc15; color: #020617;
                    border-radius: 26px; font-size: 16px; font-weight: 900;
                    border: 3px solid #fef08a;
                }
                QPushButton:hover { background-color: #fde047; }
            """)
            btn.clicked.connect(lambda checked, idx=i: self.hit_point(idx))
            grid.addWidget(btn, r, c)
            self.point_buttons.append(btn)

        main_layout.addWidget(self.canvas_frame, stretch=1)

        footer = QHBoxLayout()
        self.progress_lbl = QLabel("Progresso: 0 / 5 pontos")
        self.progress_lbl.setStyleSheet("color: #cbd5e1; font-family: Consolas, monospace; font-size: 13px;")
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #cbd5e1;
                padding: 8px 16px; border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        cancel_btn.clicked.connect(self.reject)

        footer.addStretch()
        footer.addWidget(self.progress_lbl)
        footer.addSpacing(16)
        footer.addWidget(cancel_btn)
        footer.addStretch()
        main_layout.addLayout(footer)

        self.update_ui()

    def hit_point(self, idx: int):
        if idx != self.calib_step:
            return
        self.calib_step += 1
        if self.calib_step >= 5:
            self.calibration_finished.emit()
            self.accept()
        else:
            self.update_ui()

    def update_ui(self):
        for i, btn in enumerate(self.point_buttons):
            btn.setVisible(i == self.calib_step)
        self.progress_lbl.setText(f"Progresso: {self.calib_step} / 5 pontos")


class CalibrationModal(QDialog):
    # Emite: (left_ratios, right_ratios, center_ratios, ear_samples)
    calibration_finished = pyqtSignal(list, list, list, list)

    def __init__(self, tracker_engine, parent=None):
        super().__init__(parent)
        self.tracker = tracker_engine
        self.setWindowTitle("Calibração Ocular Assistiva")
        self.setModal(True)
        self.resize(920, 640)
        self.setStyleSheet("QDialog { background-color: #020617; color: #ffffff; }")

        self.calib_step = 0
        self.hold_seconds = 2.0
        self.step_start_time = time.perf_counter()

        # Armazenamento de medições por ponto
        self.samples_per_step = {0: [], 1: [], 2: [], 3: [], 4: []}

        # Ordem dos pontos: 0: Centro, 1: Canto Superior Esq, 2: Canto Superior Dir, 3: Inf Esq, 4: Inf Dir
        self.point_labels = [
            "1. Olhe fixamente para o CENTRO",
            "2. Olhe fixamente para o CANTO SUPERIOR ESQUERDO",
            "3. Olhe fixamente para o CANTO SUPERIOR DIREITO",
            "4. Olhe fixamente para o CANTO INFERIOR ESQUERDO",
            "5. Olhe fixamente para o CANTO INFERIOR DIREITO"
        ]

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)

        badge = QLabel("CALIBRAÇÃO BIOMÉTRICA OCULAR")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("""
            background-color: rgba(245, 158, 11, 0.2);
            color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4);
            border-radius: 10px; padding: 4px 12px; font-weight: bold; font-size: 11px;
        """)
        main_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)

        self.instruction_lbl = QLabel(self.point_labels[0])
        self.instruction_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff; margin-top: 6px;")
        main_layout.addWidget(self.instruction_lbl)

        self.canvas_frame = QFrame()
        self.canvas_frame.setStyleSheet("""
            QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; }
        """)
        grid = QGridLayout(self.canvas_frame)
        grid.setContentsMargins(32, 32, 32, 32)

        self.point_buttons = []
        positions = [(1, 1), (0, 0), (0, 2), (2, 0), (2, 2)]
        for i, (r, c) in enumerate(positions):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(60, 60)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #facc15; color: #020617;
                    border-radius: 30px; font-size: 18px; font-weight: 900;
                    border: 3px solid #fef08a;
                }
            """)
            grid.addWidget(btn, r, c)
            self.point_buttons.append(btn)

        main_layout.addWidget(self.canvas_frame, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border-radius: 4px; }
            QProgressBar::chunk { background-color: #10b981; border-radius: 4px; }
        """)
        main_layout.addWidget(self.progress_bar)

        footer = QHBoxLayout()
        self.progress_lbl = QLabel("Ponto 1 de 5")
        self.progress_lbl.setStyleSheet("color: #cbd5e1; font-family: Consolas, monospace; font-size: 13px;")
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #cbd5e1;
                padding: 8px 16px; border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        cancel_btn.clicked.connect(self.reject)

        footer.addStretch()
        footer.addWidget(self.progress_lbl)
        footer.addSpacing(16)
        footer.addWidget(cancel_btn)
        footer.addStretch()
        main_layout.addLayout(footer)

        self.update_step_ui()

        # Temporizador a 30 FPS para leitura dos dados durante a calibração
        self.calib_timer = QTimer(self)
        self.calib_timer.timeout.connect(self._calibration_tick)
        self.calib_timer.start(33)

    def update_step_ui(self):
        for i, btn in enumerate(self.point_buttons):
            btn.setVisible(i == self.calib_step)
        if self.calib_step < len(self.point_labels):
            self.instruction_lbl.setText(self.point_labels[self.calib_step])
            self.progress_lbl.setText(f"Ponto {self.calib_step + 1} de 5")

    def _calibration_tick(self):
        now = time.perf_counter()
        elapsed = now - self.step_start_time
        pct = int(min(100, (elapsed / self.hold_seconds) * 100))
        self.progress_bar.setValue(pct)

        # Recolhe os rácios da câmara processados pelo tracker
        if self.tracker and hasattr(self.tracker, 'last_gaze_ratio'):
            self.samples_per_step[self.calib_step].append((self.tracker.last_gaze_ratio, self.tracker.last_ear))

        if elapsed >= self.hold_seconds:
            self.calib_step += 1
            self.step_start_time = time.perf_counter()

            if self.calib_step >= 5:
                self.calib_timer.stop()
                self._finish_and_emit()
            else:
                self.update_step_ui()

    def _finish_and_emit(self):
        # Separa amostras de centro, esquerda e direita
        center_samples = [s[0] for s in self.samples_per_step[0]]
        left_samples = [s[0] for s in self.samples_per_step[1] + self.samples_per_step[3]]
        right_samples = [s[0] for s in self.samples_per_step[2] + self.samples_per_step[4]]

        all_ears = [s[1] for step in self.samples_per_step.values() for s in step]

        self.calibration_finished.emit(left_samples, right_samples, center_samples, all_ears)
        self.accept()
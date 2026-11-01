# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar


class SelectableCardWidget(QFrame):
    clicked = pyqtSignal(int)
    hovered = pyqtSignal(int)

    def __init__(self, index: int, is_action_button: bool = False, is_emergency: bool = False):
        super().__init__()
        self.index = index
        self.is_action_button = is_action_button
        self.is_emergency = is_emergency
        self.is_focused = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)

        top_row = QHBoxLayout()
        self.num_label = QLabel(f"#{index + 1}" if not is_action_button else f"Opção {index + 1}")
        self.num_label.setStyleSheet(
            "color: #94a3b8; font-size: 11px; font-weight: bold;"
            if not is_action_button else
            "color: #fecaca; font-size: 11px; font-weight: bold;"
        )
        self.focus_badge = QLabel("FOCADO")
        self.focus_badge.setStyleSheet("""
            background-color: #facc15; color: #020617;
            font-size: 10px; font-weight: 900; padding: 2px 8px; border-radius: 8px;
        """)
        self.focus_badge.setVisible(False)

        top_row.addWidget(self.num_label)
        top_row.addStretch()
        top_row.addWidget(self.focus_badge)
        layout.addLayout(top_row)

        layout.addStretch()
        self.title_label = QLabel("")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setVisible(is_action_button)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()

        self.dwell_bar = QProgressBar()
        self.dwell_bar.setRange(0, 100)
        self.dwell_bar.setValue(0)
        self.dwell_bar.setTextVisible(False)
        self.dwell_bar.setFixedHeight(6)
        self.dwell_bar.setStyleSheet("""
            QProgressBar { background-color: transparent; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #facc15; border-radius: 3px; }
        """)
        layout.addWidget(self.dwell_bar)

        self.update_style()

    def set_content(self, title: str, subtitle: str = ""):
        self.title_label.setText(title)
        if subtitle:
            self.subtitle_label.setText(subtitle)

    def set_focused(self, focused: bool):
        self.is_focused = focused
        self.focus_badge.setVisible(focused)
        if not focused:
            self.dwell_bar.setValue(0)
        self.update_style()

    def set_dwell_progress(self, pct: int):
        self.dwell_bar.setValue(pct if self.is_focused else 0)

    def update_style(self):
        border_rule = "4px solid #facc15" if self.is_focused else "2px solid #cbd5e1"
        if self.is_action_button:
            bg_color = "#dc2626" if self.is_emergency else "#991b1b"
            border_rule = "4px solid #facc15" if self.is_focused else "3px solid transparent"
            self.setStyleSheet(f"""
                SelectableCardWidget {{
                    background-color: {bg_color};
                    border: {border_rule};
                    border-radius: 16px;
                }}
            """)
            self.title_label.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: 900; border: none;")
            self.subtitle_label.setStyleSheet("color: #fecaca; font-size: 11px; font-weight: 600; border: none;")
        else:
            bg_color = "#fefce8" if self.is_focused else "#ffffff"
            self.setStyleSheet(f"""
                SelectableCardWidget {{
                    background-color: {bg_color};
                    border: {border_rule};
                    border-radius: 16px;
                }}
            """)
            self.title_label.setStyleSheet("color: #0f172a; font-size: 22px; font-weight: 800; border: none;")

    def enterEvent(self, event):
        self.hovered.emit(self.index)
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)
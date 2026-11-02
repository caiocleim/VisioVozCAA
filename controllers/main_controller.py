import time
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QKeyEvent

from models.data import CATEGORIES, TOTAL_ITEMS
from models.services import AssistiveServices
from models.telemetry import TelemetryLogger
from models.tracker import EyeTrackerEngine
from views.main_window import CAAOcularMainWindow
from views.modals import CalibrationModal


class MainController:
    """Controlador MVC: gerencia temporizadores, regras de dwell time e atualizações de View."""

    def __init__(self, view: CAAOcularMainWindow):
        self.view = view

        # Models
        self.services = AssistiveServices()
        self.logger = TelemetryLogger()
        self.tracker = EyeTrackerEngine()

        # Estados de navegação
        self.current_category_index = 0
        self.current_focus_index = 0
        self.tracking_mode = "webcam"
        self.dwell_threshold_ms = 1000
        self.dwell_start_time = None
        self.eyes_detected = False

        self.current_gaze_direction = "CENTER"
        self.gaze_hold_start_time = 0.0
        self.last_tab_switch_time = 0.0
        self.GAZE_HOLD_CONFIRM_MS = 240
        self.TAB_SWITCH_COOLDOWN_MS = 1200

        self.last_wink_time = 0.0
        self.WINK_COOLDOWN_MS = 600
        self.EAR_THRESHOLD = 0.205

        self.sim_blink_active = False
        self.sim_light_level = 55
        self.ear_left_val = 0.29
        self.ear_right_val = 0.29

        self.frame_counter = 0
        self.last_fps_time = time.perf_counter()
        self.last_photo_time = time.perf_counter()

        self._connect_signals()
        self.render_categories_and_cards()
        self.set_tracking_mode("webcam")

        # Loop principal (30 FPS)
        self.main_timer = QTimer()
        self.main_timer.timeout.connect(self.main_loop)
        self.main_timer.start(33)

    def _connect_signals(self):
        # Header
        self.view.btn_mode_sim.clicked.connect(lambda: self.set_tracking_mode("simulation"))
        self.view.btn_mode_cam.clicked.connect(lambda: self.set_tracking_mode("webcam"))
        self.view.dwell_slider.valueChanged.connect(self.change_dwell_time)
        self.view.btn_webcam_info.clicked.connect(self.view.webcam_modal.show)
        self.view.btn_calib.clicked.connect(self.open_calibration_modal)
        self.view.btn_mute.clicked.connect(self.toggle_mute_tts)
        self.view.btn_csv.clicked.connect(self.export_telemetry_csv)

        self.view.sim_light_slider.valueChanged.connect(self.change_simulated_light)

        # Botões manuais
        self.view.btn_prev.clicked.connect(lambda: self.navigate_step(-1))
        self.view.btn_next.clicked.connect(lambda: self.navigate_step(1))
        self.view.btn_sel.pressed.connect(self.start_blink)
        self.view.btn_sel.released.connect(self.end_blink)
        self.view.btn_tab_l.clicked.connect(lambda: self.trigger_gaze_tab_switch(-1))
        self.view.btn_tab_r.clicked.connect(lambda: self.trigger_gaze_tab_switch(1))

        # Abas
        for idx, btn in enumerate(self.view.tab_buttons):
            btn.clicked.connect(lambda checked, i=idx: self.set_category(i, by_gaze=False))

        # Cartões: Clique e Passagem de Mouse (Hover)
        for card in self.view.card_widgets:
            card.clicked.connect(self.user_click_item)
            card.hovered.connect(self.on_card_hovered)

        self.view.keyPressed.connect(self.handle_key_press)
        self.view.keyReleased.connect(self.handle_key_release)
        self.view.closeEvent = self.on_close_event

    def render_categories_and_cards(self):
        for i, btn in enumerate(self.view.tab_buttons):
            if i == self.current_category_index:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff; color: #0f172a;
                        border: 2px solid #0f172a; border-radius: 10px;
                        padding: 8px 18px; font-size: 14px; font-weight: 900;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #cbd5e1; color: #334155;
                        border: none; border-radius: 10px;
                        padding: 8px 18px; font-size: 14px; font-weight: 600;
                    }
                    QPushButton:hover { background-color: #e2e8f0; }
                """)

        cards_data = CATEGORIES[self.current_category_index]["cards"]
        for idx, card_info in enumerate(cards_data):
            self.view.card_widgets[idx].set_content(card_info["title"])

        for idx, widget in enumerate(self.view.card_widgets):
            widget.set_focused(idx == self.current_focus_index)

        titles = [
            f"Cartão #{i + 1} ({c['title'].replace(chr(10), ' ')})"
            for i, c in enumerate(cards_data)
        ] + ["Opção 7: CHAMAR CUIDADOR", "Opção 8: ALERTA DE EMERGÊNCIA"]

        self.view.focus_title_lbl.setText(f"Foco Atual: {titles[self.current_focus_index]}")
        self.view.focus_item_counter.setText(f"Opção Atual: {self.current_focus_index + 1} / 8")

    def set_focus(self, new_index: int, play_sound: bool = True, move_mouse: bool = True):
        """Método unificado para mudar a opção focada e disparar feedback auditivo."""
        new_index = (new_index + TOTAL_ITEMS) % TOTAL_ITEMS
        if new_index == self.current_focus_index:
            return

        self.current_focus_index = new_index
        self.render_categories_and_cards()

        if play_sound:
            self.services.play_step_sound()

        if move_mouse:
            self.services.move_cursor_to_widget(self.view.card_widgets[self.current_focus_index])

    def on_card_hovered(self, index: int):
        """Disparado quando o cursor do mouse passa por cima de uma opção."""
        if index != self.current_focus_index:
            self.set_focus(index, play_sound=True, move_mouse=False)

    def set_category(self, idx: int, by_gaze: bool = False):
        self.current_category_index = (idx + len(CATEGORIES)) % len(CATEGORIES)
        self.current_focus_index = 0
        self.render_categories_and_cards()
        self.services.play_tab_sound()

        cat_name = CATEGORIES[self.current_category_index]["name"]
        prefix = "Olhar detectado: Aba alterada para" if by_gaze else "Aba selecionada:"
        self.view.feedback_action_text.setText(f'Status do Comando: {prefix} "{cat_name}"')

        self.logger.log_event(
            self.tracking_mode, "TROCA_ABA_OLHAR" if by_gaze else "TROCA_ABA_MANUAL",
            cat_name, self.ear_left_val, self.ear_right_val,
            self.current_gaze_direction, self.tracker.telemetry["luminosity"],
            self.tracker.telemetry["qualityRating"], self.tracker.telemetry["fps"]
        )

    def trigger_gaze_tab_switch(self, direction: int):
        now_ms = time.perf_counter() * 1000.0
        if now_ms - self.last_tab_switch_time < self.TAB_SWITCH_COOLDOWN_MS:
            return
        self.last_tab_switch_time = now_ms
        self.set_category(self.current_category_index + direction, by_gaze=True)

    def navigate_step(self, delta: int):
        self.set_focus(self.current_focus_index + delta, play_sound=True, move_mouse=True)

    def user_click_item(self, index: int):
        self.set_focus(index, play_sound=False, move_mouse=False)
        self.execute_item(index)

    def execute_item(self, index: int):
        self.services.play_select_sound()

        if 0 <= index <= 5:
            card = CATEGORIES[self.current_category_index]["cards"][index]
            title_clean = card["title"].replace("\n", " ")
            speech_msg = card["speech"]
            self.services.speak(speech_msg, is_emergency=False)
            self.services.send_local_notification("COMUNICACAO_CARTAO", title_clean, speech_msg)
            self.view.feedback_action_text.setText(f'Status do Comando: "{title_clean}" — {speech_msg}')
            target_name = title_clean
        elif index == 6:
            msg = "Atenção cuidador! O paciente está chamando no quarto!"
            self.services.speak(msg, is_emergency=False)
            self.services.send_local_notification("CHAMAR_CUIDADOR", "CHAMAR CUIDADOR", msg)
            self.view.feedback_action_text.setText("Status do Comando: 🔔 CHAMAR CUIDADOR ACIONADO!")
            target_name = "CHAMAR_CUIDADOR"
        else:
            msg = "Alerta de emergência! O paciente precisa de socorro imediato!"
            self.services.speak(msg, is_emergency=True)
            self.services.send_local_notification("ALERTA_EMERGENCIA", "ALERTA DE EMERGÊNCIA", msg)
            self.view.feedback_action_text.setText("Status do Comando: 🚨 ALERTA DE EMERGÊNCIA ACIONADO!")
            target_name = "ALERTA_EMERGENCIA"

        self.logger.log_event(
            self.tracking_mode, "SELECAO_DWELL_TIME", target_name,
            self.ear_left_val, self.ear_right_val, self.current_gaze_direction,
            self.tracker.telemetry["luminosity"], self.tracker.telemetry["qualityRating"], self.tracker.telemetry["fps"]
        )

    def set_tracking_mode(self, mode: str):
        self.tracking_mode = mode
        active_css = "background-color: #059669; color: #ffffff; border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 11px;"
        inactive_css = "background-color: #1e293b; color: #cbd5e1; border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 11px;"

        if mode == "simulation":
            self.tracker.stop_camera()
            self.view.btn_mode_sim.setStyleSheet(active_css)
            self.view.btn_mode_cam.setStyleSheet(inactive_css)
            self.tracker.telemetry["name"] = "Simulador de Rastreamento Ocular"
            self.view.sim_light_frame.setVisible(True)
            self.view.feedback_action_text.setText("Status do Comando: Modo Simulação ativo! Use as teclas Q, E, A, D e Espaço.")
        else:
            self.view.btn_mode_cam.setStyleSheet(active_css)
            self.view.btn_mode_sim.setStyleSheet(inactive_css)
            self.view.sim_light_frame.setVisible(False)
            success = self.tracker.start_camera()
            if not success:
                self.set_tracking_mode("simulation")
                self.view.feedback_action_text.setText("Status do Comando: Câmera indisponível. Alternado para Simulação.")
            else:
                self.view.tracking_status_badge.setText("Webcam Espelhada")
                self.view.feedback_action_text.setText("Status do Comando: Rastreamento ativo! Olhe para os lados para alternar abas.")

    def change_simulated_light(self, val: int):
        self.sim_light_level = int(val)
        desc = "Ideal"
        if self.sim_light_level < 25:
            desc = "Muito Baixa"
        elif self.sim_light_level > 80:
            desc = "Excessiva"
        self.view.sim_light_label.setText(f"Iluminação de Teste: {self.sim_light_level}% ({desc})")

    def change_dwell_time(self, val: int):
        self.dwell_threshold_ms = int(val)
        self.view.dwell_val_display.setText(f"{self.dwell_threshold_ms / 1000.0:.1f}s")

    def toggle_mute_tts(self):
        self.services.tts_muted = not self.services.tts_muted
        if self.services.tts_muted:
            self.view.btn_mute.setText("🔇 Mudo")
            self.view.btn_mute.setStyleSheet("background-color: #1e293b; color: #fb7185; border: 1px solid #334155; border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 11px;")
        else:
            self.view.btn_mute.setText("🔊 Voz Ativa")
            self.view.btn_mute.setStyleSheet("background-color: #1e293b; color: #34d399; border: 1px solid #334155; border-radius: 6px; padding: 5px 10px; font-weight: bold; font-size: 11px;")

    def start_blink(self):
        if not self.sim_blink_active:
            self.sim_blink_active = True
            self.dwell_start_time = time.perf_counter() * 1000.0

    def end_blink(self):
        self.sim_blink_active = False
        self.dwell_start_time = None
        self.view.update_dwell_visuals(0, self.current_focus_index)

    def main_loop(self):
        now_sec = time.perf_counter()
        now_ms = now_sec * 1000.0
        self.frame_counter += 1

        if now_sec - self.last_fps_time >= 1.0:
            self.tracker.telemetry["fps"] = self.frame_counter
            self.frame_counter = 0
            self.last_fps_time = now_sec

        if self.tracking_mode == "webcam":
            success, frame, ear_l, ear_r, gaze_dir, detected = self.tracker.process_frame()
            if not success or frame is None:
                self.set_tracking_mode("simulation")
                return

            self.eyes_detected = detected
            self.ear_left_val, self.ear_right_val = ear_l, ear_r
            self.current_gaze_direction = gaze_dir

            if detected:
                self.view.badge_ear_l.setText(f"OE (Esq): {ear_l:.2f}")
                self.view.badge_ear_r.setText(f"OD (Dir): {ear_r:.2f}")

                is_left_closed = ear_l < self.EAR_THRESHOLD
                is_right_closed = ear_r < self.EAR_THRESHOLD

                if is_left_closed and is_right_closed:
                    if self.dwell_start_time is None:
                        self.dwell_start_time = now_ms
                    self.view.tracking_status_badge.setText("Confirmando (2 Olhos)...")
                else:
                    if self.dwell_start_time is not None:
                        self.dwell_start_time = None
                        self.view.update_dwell_visuals(0, self.current_focus_index)
                    self.view.tracking_status_badge.setText("Olhos Detectados")

                    # Piscada unilateral (navegação)
                    if is_right_closed and not is_left_closed and (now_ms - self.last_wink_time > self.WINK_COOLDOWN_MS):
                        self.last_wink_time = now_ms
                        self.navigate_step(1)
                    elif is_left_closed and not is_right_closed and (now_ms - self.last_wink_time > self.WINK_COOLDOWN_MS):
                        self.last_wink_time = now_ms
                        self.navigate_step(-1)

                    # Olhar sustentado (troca de abas)
                    if not is_left_closed and not is_right_closed:
                        self.view.update_gaze_hud(gaze_dir)
                        if gaze_dir != "CENTER":
                            if self.gaze_hold_start_time == 0.0:
                                self.gaze_hold_start_time = now_ms
                            elif now_ms - self.gaze_hold_start_time >= self.GAZE_HOLD_CONFIRM_MS:
                                self.trigger_gaze_tab_switch(1 if gaze_dir == "RIGHT" else -1)
                                self.gaze_hold_start_time = 0.0
                        else:
                            self.gaze_hold_start_time = 0.0
            else:
                self.view.update_gaze_hud("CENTER")
                self.view.tracking_status_badge.setText("Rosto Ausente")

            self.view.display_opencv_frame(frame)
        else:
            self.eyes_detected = self.sim_light_level >= 15
            self.view.tracking_status_badge.setText("Olhos Detectados (Sim)" if self.eyes_detected else "Luz Baixa (Sem Sinal)")
            frame = self.tracker.generate_simulated_frame(self.sim_light_level, self.sim_blink_active)
            self.ear_left_val = 0.13 if self.sim_blink_active else 0.29
            self.ear_right_val = 0.13 if self.sim_blink_active else 0.29
            self.view.badge_ear_l.setText(f"OE (Esq): {self.ear_left_val:.2f}")
            self.view.badge_ear_r.setText(f"OD (Dir): {self.ear_right_val:.2f}")
            self.view.display_opencv_frame(frame)

        if now_sec - self.last_photo_time >= 0.25:
            self.last_photo_time = now_sec
            self.tracker.calculate_photometrics(self.eyes_detected)
            self.view.update_telemetry_hud(self.tracker.telemetry)

        if self.dwell_start_time is not None:
            elapsed = now_ms - self.dwell_start_time
            pct = (elapsed / self.dwell_threshold_ms) * 100.0
            self.view.update_dwell_visuals(pct, self.current_focus_index)

            if elapsed >= self.dwell_threshold_ms:
                selected = self.current_focus_index
                self.dwell_start_time = None
                self.sim_blink_active = False
                self.view.update_dwell_visuals(0, self.current_focus_index)
                self.execute_item(selected)

    def open_calibration_modal(self):
        # Passa a instância do tracker para o modal recolher os rácios
        modal = CalibrationModal(self.tracker, self.view)
        modal.calibration_finished.connect(self._on_calibration_completed)
        modal.exec()

    def _on_calibration_completed(self, left_ratios, right_ratios, center_ratios, ear_samples):
        # 1. Regula os parâmetros do motor matemático
        self.tracker.apply_calibration(left_ratios, right_ratios, center_ratios, ear_samples)

        # 2. Atualiza o limiar de fecho dos olhos do próprio controlador
        self.EAR_THRESHOLD = self.tracker.calibrated_ear_threshold

        # 3. Notifica a View e o utilizador
        self.view.feedback_action_text.setText(
            f"Status do Comando: Calibração Concluída! Limiar EAR ajustado para {self.EAR_THRESHOLD:.2f}."
        )
        self.services.speak("Calibração ocular concluída com sucesso e parâmetros atualizados!")

        self.logger.log_event(
            self.tracking_mode, "CALIBRACAO_5_PONTOS_CONCLUIDA", "CALIBRACAO_APLICADA",
            self.ear_left_val, self.ear_right_val, self.current_gaze_direction,
            self.tracker.telemetry["luminosity"], self.tracker.telemetry["qualityRating"], self.tracker.telemetry["fps"]
        )

    def export_telemetry_csv(self):
        self.logger.log_event(
            self.tracking_mode, "EXPORTACAO_RELATORIO", "CSV",
            self.ear_left_val, self.ear_right_val, self.current_gaze_direction,
            self.tracker.telemetry["luminosity"], self.tracker.telemetry["qualityRating"], self.tracker.telemetry["fps"]
        )
        path = self.logger.export_csv()
        if path:
            self.view.feedback_action_text.setText(f"Status do Comando: Relatório exportado para: {path}")
            self.services.speak("Relatório de telemetria salvo com sucesso.")

    def handle_key_press(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_E):
            self.navigate_step(1)
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Q):
            self.navigate_step(-1)
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.trigger_gaze_tab_switch(1)
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.trigger_gaze_tab_switch(-1)
        elif key == Qt.Key.Key_1:
            self.set_category(0)
        elif key == Qt.Key.Key_2:
            self.set_category(1)
        elif key == Qt.Key.Key_3:
            self.set_category(2)
        elif key == Qt.Key.Key_Space:
            self.start_blink()

    def handle_key_release(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            self.end_blink()

    def on_close_event(self, event):
        self.tracker.stop_camera()
        self.logger.export_csv()
        event.accept()
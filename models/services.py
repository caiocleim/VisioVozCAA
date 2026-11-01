# -*- coding: utf-8 -*-
import io
import wave
import queue
import threading
import asyncio
from datetime import datetime

import numpy as np
import edge_tts
import pygame
import requests
import pyautogui

if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

pyautogui.FAILSAFE = False


class AssistiveServices:
    """Síntese de voz neural via edge-tts, efeitos sonoros de interface e notificações."""

    def __init__(
        self,
        voice: str = "pt-BR-FranciscaNeural",
        webhook_url: str = "http://127.0.0.1:8080/api/notificacao",
    ):
        self.tts_muted = False
        self.voice = voice
        self.webhook_url = webhook_url
        self.speech_queue = queue.Queue()

        self._init_ui_sounds()

        self.worker_thread = threading.Thread(
            target=self._tts_worker, daemon=True
        )
        self.worker_thread.start()

    def _generate_sound(self, start_freq: float, end_freq: float, duration_ms: int, volume: float = 0.40) -> pygame.mixer.Sound:
        sample_rate = 44100
        n_samples = int(sample_rate * (duration_ms / 1000.0))

        freqs = np.linspace(start_freq, end_freq, n_samples)
        phase = 2 * np.pi * np.cumsum(freqs) / sample_rate

        envelope = np.ones(n_samples)
        attack_samples = max(1, int(sample_rate * 0.008))
        envelope[:attack_samples] = np.linspace(0.0, 1.0, attack_samples)
        envelope[attack_samples:] = np.linspace(1.0, 0.0, n_samples - attack_samples) ** 1.8

        audio = (np.sin(phase) * envelope * volume * 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        buf.seek(0)

        return pygame.mixer.Sound(buf)

    def _init_ui_sounds(self):
        try:
            # 1. Passo entre opções: Tom tipo 'pop/click' nítido (85ms, 750Hz -> 600Hz)
            self.snd_step = self._generate_sound(750, 600, 85, volume=0.15)

            # 2. Troca de aba: Tom duplo ascendente (100ms, 480Hz -> 820Hz)
            self.snd_tab = self._generate_sound(480, 820, 100, volume=0.35)

            # 3. Confirmação / Seleção: Tom agudo (130ms, 950Hz -> 1350Hz)
            self.snd_select = self._generate_sound(950, 1350, 130, volume=0.45)
        except Exception as e:
            print(f"Aviso áudio UI: {e}")
            self.snd_step = None
            self.snd_tab = None
            self.snd_select = None

    def play_step_sound(self):
        if not self.tts_muted and self.snd_step:
            self.snd_step.play()

    def play_tab_sound(self):
        if not self.tts_muted and self.snd_tab:
            self.snd_tab.play()

    def play_select_sound(self):
        if not self.tts_muted and self.snd_select:
            self.snd_select.play()

    def _tts_worker(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            item = self.speech_queue.get()
            if item is None:
                break
            text, is_emergency = item

            if not self.tts_muted:
                try:
                    rate = "+20%" if is_emergency else "+0%"
                    communicate = edge_tts.Communicate(text, self.voice, rate=rate)
                    mp3_data = bytearray()

                    async def _collect():
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                mp3_data.extend(chunk["data"])

                    loop.run_until_complete(_collect())

                    audio_stream = io.BytesIO(mp3_data)
                    pygame.mixer.music.load(audio_stream)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(20)
                except Exception as e:
                    print(f"Aviso TTS: {e}")

            self.speech_queue.task_done()

    def speak(self, text: str, is_emergency: bool = False):
        if self.tts_muted:
            return
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
        self.speech_queue.put((text, is_emergency))

    def send_local_notification(self, event_type: str, title: str, message: str):
        def _post():
            payload = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "title": title,
                "message": message,
                "origin": "CAA_Ocular_Assistivo",
            }
            try:
                requests.post(self.webhook_url, json=payload, timeout=1.2)
            except requests.RequestException:
                pass

        threading.Thread(target=_post, daemon=True).start()

    def move_cursor_to_widget(self, widget):
        try:
            global_pos = widget.mapToGlobal(widget.rect().center())
            pyautogui.moveTo(global_pos.x(), global_pos.y(), duration=0.05)
        except Exception:
            pass
from datetime import datetime
import pandas as pd


class TelemetryLogger:
    """Registra eventos de interação, métricas oculares e iluminação com Pandas."""

    def __init__(self, csv_filename: str = "relatorio_telemetria_caa.csv"):
        self.csv_filename = csv_filename
        self.records = []

    def log_event(self, mode: str, event_type: str, target_item: str, ear_l: float,
                  ear_r: float, gaze_dir: str, luminosity: float, quality: int, fps: int):
        self.records.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "modo_operacao": mode,
            "evento": event_type,
            "item_alvo": target_item,
            "ear_esquerdo": round(ear_l, 3),
            "ear_direito": round(ear_r, 3),
            "direcao_olhar": gaze_dir,
            "luminosidade_pct": round(luminosity, 2),
            "quality_rating_pct": int(quality),
            "fps": int(fps)
        })

    def export_csv(self) -> str:
        if not self.records:
            return ""
        df = pd.DataFrame(self.records)
        df.to_csv(self.csv_filename, index=False, encoding="utf-8-sig")
        return self.csv_filename
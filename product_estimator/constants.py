from __future__ import annotations
from dataclasses import dataclass


FATOR_CUBAGEM = 6000
MODEL_TEMPERATURE = 0.0


DIMENSION_INTERVAL_CALIBRATION_MULTIPLIER = 1.64
WEIGHT_INTERVAL_CALIBRATION_MULTIPLIER = 1.96
MIN_DIMENSION_RANGE_VALUE_CM = 0.1
MIN_WEIGHT_RANGE_VALUE_KG = 0.001
MIN_DIMENSION_DISPLAY_VALUE_CM = 1
MIN_WEIGHT_DISPLAY_VALUE_KG = 0.01
DIMENSION_DISPLAY_DECIMAL_PLACES = 1
WEIGHT_DISPLAY_DECIMAL_PLACES = 2
DIMENSION_INTERVAL_CALIBRATION = {
    "comprimento": {"bias": 0.3905, "std": 1.9992},
    "largura": {"bias": 0.2189, "std": 2.1121},
    "altura": {"bias": 0.5584, "std": 1.3819},
}
WEIGHT_INTERVAL_CALIBRATION = (
    {"class": "leve", "max_estimate_kg": 0.1, "bias": 0.0024, "std": 0.0244},
    {"class": "medio", "max_estimate_kg": 0.5, "bias": 0.0339, "std": 0.0790},
    {"class": "pesado", "max_estimate_kg": None, "bias": 0.3431, "std": 0.6567},
)


DIMENSION_KEYS = ("comprimento", "largura", "altura")
RANGE_KEYS = ("min", "max", "estimativa")
MEASURED_OBJECT_KEYS = ("produto",)
CONFIDENCE_LEVELS = {"baixo", "alto"}
KNOWN_MEASURE_LABELS = {
    "comprimento": "comprimento conhecido",
    "largura": "largura conhecida",
    "altura": "altura conhecida",
    "peso": "peso conhecido",
}

KNOWN_MEASURE_UNITS = {
    "comprimento": "cm",
    "largura": "cm",
    "altura": "cm",
    "peso": "kg",
}


@dataclass
class Objeto:
    x: int | float
    y: int | float
    z: int | float
    w: int | float

    @classmethod
    def from_dict(cls, data: dict) -> "Objeto":
        return cls(
            x=data["dimensoes_estimadas_cm"]["comprimento"]["estimativa"],
            y=data["dimensoes_estimadas_cm"]["largura"]["estimativa"],
            z=data["dimensoes_estimadas_cm"]["altura"]["estimativa"],
            w=data["peso_estimado_kg"]["estimativa"],
        )

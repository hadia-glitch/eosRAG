"""One feature contract for training and serving; no outcome/culture features.

History is relative to birth in hours. Only measurements known at the index
time are accepted. Trends use actual time, not row order or a hand-built score.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NUMERIC = {
    "gestational_age_weeks": (22, 44), "birth_weight_g": (200, 6500),
    "maternal_temperature": (32, 43), "rom_hours": (0, 336),
    "neonatal_temperature": (30, 43), "heart_rate": (30, 300),
    "respiratory_rate": (0, 150), "spo2": (20, 100),
    "crp_level": (0, 600), "wbc_count": (0, 200000),
    "platelet_count": (0, 2000000), "pct_level": (0, 1000),
    "it_ratio": (0, 1), "creatinine_mg_dl": (0, 20),
    "urine_output_ml_kg_hr": (0, 30), "apgar_5_min": (0, 10),
}
BOOLEAN = ("gbs_positive", "adequate_intrapartum_antibiotics", "clinical_chorioamnionitis", "poor_perfusion")
CATEGORIES = {
    "respiratory_distress": ("None", "Mild", "Severe"),
    "oxygen_need": ("None", "Supplemental", "CPAP/Ventilation"),
    "neurological_status": ("Normal", "Irritable/Lethargic", "Seizures"),
}
TREND_FIELDS = ("neonatal_temperature", "heart_rate", "respiratory_rate", "spo2", "crp_level", "wbc_count", "platelet_count", "creatinine_mg_dl")
FEATURE_VERSION = "eos-landmark-v1"
FEATURE_NAMES = ("age_hours", *NUMERIC, *BOOLEAN,
                 *(f"{k}__{v}" for k, values in CATEGORIES.items() for v in values),
                 *(f"{k}__{s}" for k in TREND_FIELDS for s in ("slope_per_hour", "delta", "count")))


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    age_hours: float = Field(ge=0, le=72)
    values: dict[str, float | bool | str | None] = Field(default_factory=dict, max_length=40)

    @model_validator(mode="after")
    def check_values(self):
        allowed = set(NUMERIC) | set(BOOLEAN) | set(CATEGORIES)
        for key, value in self.values.items():
            if key not in allowed:
                raise ValueError(f"Unsupported predictor: {key}")
            if value is None:
                continue
            if key in NUMERIC:
                lo, hi = NUMERIC[key]
                if isinstance(value, (bool, str)) or not math.isfinite(value) or not lo <= value <= hi:
                    raise ValueError(f"{key} outside accepted units/range [{lo}, {hi}]")
            elif key in BOOLEAN and not isinstance(value, bool):
                raise ValueError(f"{key} must be boolean or null")
            elif key in CATEGORIES and value not in CATEGORIES[key]:
                raise ValueError(f"Unknown {key} category")
        return self


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    current: Observation
    history: list[Observation] = Field(default_factory=list, max_length=200)
    purpose: Literal["research", "clinical"] = "research"

    @model_validator(mode="after")
    def check_history(self):
        times = [o.age_hours for o in self.history]
        if any(t >= self.current.age_hours for t in times):
            raise ValueError("History must precede the prediction time")
        if len(times) != len(set(times)):
            raise ValueError("Duplicate history timestamps require aggregation before prediction")
        return self


def extract_features(request: PredictionRequest) -> dict[str, float | None]:
    current = request.current
    values = current.values
    out = {name: None for name in FEATURE_NAMES}
    out["age_hours"] = current.age_hours
    for key in (*NUMERIC, *BOOLEAN):
        v = values.get(key)
        out[key] = float(v) if v is not None else None
    for key, categories in CATEGORIES.items():
        for category in categories:
            out[f"{key}__{category}"] = float(values[key] == category) if values.get(key) is not None else None
    window = sorted([o for o in request.history if current.age_hours - o.age_hours <= 24] + [current], key=lambda o: o.age_hours)
    for key in TREND_FIELDS:
        pairs = [(o.age_hours, float(o.values[key])) for o in window if o.values.get(key) is not None]
        out[f"{key}__count"] = float(len(pairs))
        if len(pairs) >= 2:
            xs, ys = zip(*pairs)
            xbar, ybar = sum(xs) / len(xs), sum(ys) / len(ys)
            denom = sum((x - xbar) ** 2 for x in xs)
            out[f"{key}__slope_per_hour"] = sum((x - xbar) * (y - ybar) for x, y in pairs) / denom if denom else None
            out[f"{key}__delta"] = ys[-1] - ys[0]
    return out

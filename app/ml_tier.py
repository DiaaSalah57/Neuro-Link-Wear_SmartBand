"""
NeuroLink Wear — Tier 3 ML anomaly detector (Isolation Forest).

Wraps the trained offline artifacts (`models/scaler.pkl`,
`models/isolation_forest.pkl`, `models/pipeline_stats.json`) as a
fail-soft, purely additive third detection tier on live telemetry.

Safety contract (identical to Tier 1 ↔ Tier 2):
  * Tier 3 can ONLY add a detection ("General Anomaly"), never suppress
    or downgrade a Tier 1 (clinical floor) or Tier 2 (personal σ-rule) alert.
  * If models or dependencies are missing, corrupt, or raise any runtime
    exception, `ml_anomaly()` returns `{"available": False, "is_anomaly": False,
    "score": 0.0}` so Tier 1 + Tier 2 continue completely unaffected.
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

NUMERIC_FEATURES = [
    "Heart_Rate", "Body_Temperature", "Blood_Oxygen", "Step_Count",
    "Accel_X", "Accel_Y", "Accel_Z",
    "Gyro_X", "Gyro_Y", "Gyro_Z",
    "GSR_Value", "HRV", "Sweat_Response",
    "Activity_Intensity",
    "Accel_Magnitude", "Gyro_Magnitude",
    "HR_HRV_Ratio", "Stress_Score",
    "SpO2_Risk", "Fever_Risk", "HR_Deviation",
    "HR_per_Activity", "HRV_Adjusted",
]

ACTIVITY_INTENSITY_MAP = {
    "Sleeping": 1,
    "Resting": 2,
    "Walking": 3,
    "Running": 4,
    "Exercising": 5,
}

# Corrected activity-expected heart rates (consistent with pipeline.py)
EXPECTED_HR = {1: 52, 2: 63, 3: 90, 4: 143, 5: 131}

DEFAULT_STATS = {
    "gsr_min": 0.1002432813694827,
    "gsr_max": 19.933999867173764,
    "hrv_min": 13.604118941971876,
    "hrv_max": 89.95592673609177,
    "if_threshold": -0.02,
}

_scaler = None
_iso_forest = None
_stats: dict | None = None
_load_failed = False


def _load_artifacts():
    """Lazily load scaler.pkl, isolation_forest.pkl, and pipeline_stats.json."""
    global _scaler, _iso_forest, _stats, _load_failed
    if _scaler is not None and _iso_forest is not None:
        return _scaler, _iso_forest, _stats or DEFAULT_STATS
    if _load_failed:
        return None, None, DEFAULT_STATS

    try:
        import joblib

        scaler_path = MODELS_DIR / "scaler.pkl"
        iso_path = MODELS_DIR / "isolation_forest.pkl"
        stats_path = MODELS_DIR / "pipeline_stats.json"

        if not scaler_path.exists() or not iso_path.exists():
            _load_failed = True
            return None, None, DEFAULT_STATS

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _scaler = joblib.load(scaler_path)
            _iso_forest = joblib.load(iso_path)

        if stats_path.exists():
            with open(stats_path, "r", encoding="utf-8") as f:
                _stats = {**DEFAULT_STATS, **json.load(f)}
        else:
            _stats = dict(DEFAULT_STATS)

        return _scaler, _iso_forest, _stats
    except Exception:
        _load_failed = True
        return None, None, DEFAULT_STATS


def build_feature_dict(reading: dict, cal: dict | None = None, stats: dict | None = None) -> dict[str, float]:
    """
    Reconstruct the 23-feature dictionary expected by `models/scaler.pkl`
    (`NUMERIC_FEATURES` in `pipeline.py`) from a live lowercase `reading` dict.
    """
    st = stats or _stats or DEFAULT_STATS

    hr = float(reading.get("heart_rate", 72.0) or 0.0)
    temp = float(reading.get("temperature", 36.6) or 0.0)
    spo2 = float(reading.get("spo2", 97.0) or 0.0)
    steps = float(reading.get("steps", 0.0) or 0.0)
    gsr = float(reading.get("gsr", 0.4) or 0.0)
    hrv = float(reading.get("hrv", 50.0) or 0.0)

    activity = reading.get("activity") or "Resting"
    intensity = int(ACTIVITY_INTENSITY_MAP.get(activity, 2))

    has_ax = reading.get("accel_x") is not None
    has_ay = reading.get("accel_y") is not None
    has_az = reading.get("accel_z") is not None
    accel_mag_in = reading.get("accel_mag")

    accel_x = float(reading["accel_x"]) if has_ax else 0.0
    accel_y = float(reading["accel_y"]) if has_ay else 0.0
    if has_az:
        accel_z = float(reading["accel_z"])
    elif accel_mag_in is not None and not has_ax and not has_ay:
        accel_z = float(accel_mag_in)
    else:
        accel_z = 1.0

    if accel_mag_in is not None:
        accel_mag = float(accel_mag_in)
    else:
        accel_mag = float(math.sqrt(accel_x ** 2 + accel_y ** 2 + accel_z ** 2))

    has_gx = reading.get("gyro_x") is not None
    has_gy = reading.get("gyro_y") is not None
    has_gz = reading.get("gyro_z") is not None
    gyro_mag_in = reading.get("gyro_mag")

    gyro_x = float(reading["gyro_x"]) if has_gx else 0.0
    gyro_y = float(reading["gyro_y"]) if has_gy else 0.0
    if has_gz:
        gyro_z = float(reading["gyro_z"])
    elif gyro_mag_in is not None and not has_gx and not has_gy:
        gyro_z = float(gyro_mag_in)
    else:
        gyro_z = 0.0

    if gyro_mag_in is not None:
        gyro_mag = float(gyro_mag_in)
    else:
        gyro_mag = float(math.sqrt(gyro_x ** 2 + gyro_y ** 2 + gyro_z ** 2))

    if reading.get("sweat_response") is not None:
        sweat_response = float(reading["sweat_response"])
    else:
        sweat_response = round(gsr * 0.36, 4)

    hr_hrv_ratio = hr / (hrv + 1e-6)
    spo2_risk = max(0.0, 98.0 - spo2)
    fever_risk = max(0.0, temp - 37.2)
    hr_deviation = hr - EXPECTED_HR.get(intensity, 63)
    hr_per_activity = hr / intensity
    hrv_adjusted = hrv * intensity

    gsr_min, gsr_max = float(st["gsr_min"]), float(st["gsr_max"])
    hrv_min, hrv_max = float(st["hrv_min"]), float(st["hrv_max"])
    stress_score = (
        (gsr - gsr_min) / (gsr_max - gsr_min + 1e-6)
        + 1.0 - (hrv - hrv_min) / (hrv_max - hrv_min + 1e-6)
    ) / 2.0

    return {
        "Heart_Rate": hr,
        "Body_Temperature": temp,
        "Blood_Oxygen": spo2,
        "Step_Count": steps,
        "Accel_X": accel_x,
        "Accel_Y": accel_y,
        "Accel_Z": accel_z,
        "Gyro_X": gyro_x,
        "Gyro_Y": gyro_y,
        "Gyro_Z": gyro_z,
        "GSR_Value": gsr,
        "HRV": hrv,
        "Sweat_Response": sweat_response,
        "Activity_Intensity": float(intensity),
        "Accel_Magnitude": accel_mag,
        "Gyro_Magnitude": gyro_mag,
        "HR_HRV_Ratio": hr_hrv_ratio,
        "Stress_Score": stress_score,
        "SpO2_Risk": spo2_risk,
        "Fever_Risk": fever_risk,
        "HR_Deviation": hr_deviation,
        "HR_per_Activity": hr_per_activity,
        "HRV_Adjusted": hrv_adjusted,
    }


def ml_anomaly(reading: dict, cal: dict | None = None) -> dict:
    """
    Evaluate a single reading with the trained Isolation Forest (Tier 3).

    Returns:
        {"available": bool, "is_anomaly": bool, "score": float}
    Never raises — fails soft with available=False on any error.
    """
    try:
        scaler, iso_forest, stats = _load_artifacts()
        if scaler is None or iso_forest is None:
            return {"available": False, "is_anomaly": False, "score": 0.0}

        import numpy as np

        feats = build_feature_dict(reading, cal, stats)
        row = np.array([[feats[f] for f in NUMERIC_FEATURES]], dtype=float)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scaled = scaler.transform(row)
            score = float(iso_forest.decision_function(scaled)[0])

        threshold = float(stats.get("if_threshold", -0.02))
        is_anom = bool(score < threshold)
        return {
            "available": True,
            "is_anomaly": is_anom,
            "score": round(score, 4),
        }
    except Exception:
        return {"available": False, "is_anomaly": False, "score": 0.0}

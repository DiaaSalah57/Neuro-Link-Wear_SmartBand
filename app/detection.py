"""
NeuroLink Wear — anomaly detection engine.

Real-time rule/ensemble detection for the four flagship conditions
(High Stress, Fever, Low Oxygen, Fall Detection) plus tachycardia,
bradycardia, fatigue and inactivity. Thresholds are per-patient and fully
editable from the dashboard's Management view.

The stress score reproduces the feature engineering from pipeline.py
(GSR + inverted HRV normalised against the training stats), so the live
engine and the offline ML pipeline agree on the definition of "stress".
"""
from __future__ import annotations

from datetime import datetime, timezone

# Training-set normalisation bounds (from models/pipeline_stats.json)
GSR_MIN, GSR_MAX = 0.10, 19.93
HRV_MIN, HRV_MAX = 13.60, 89.96

ACTIVITY_INTENSITY = {
    "Sleeping": 1, "Resting": 2, "Walking": 3, "Running": 4, "Exercising": 5,
}
EXPECTED_HR = {1: 62, 2: 75, 3: 100, 4: 155, 5: 145}

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def stress_score(gsr: float, hrv: float) -> float:
    """Normalised 0..1 stress index — same formula as pipeline.build_features."""
    gsr_part = (gsr - GSR_MIN) / (GSR_MAX - GSR_MIN + 1e-6)
    hrv_part = 1 - (hrv - HRV_MIN) / (HRV_MAX - HRV_MIN + 1e-6)
    return round(max(0.0, min(1.0, (gsr_part + hrv_part) / 2)), 3)


def expected_hr(activity: str, age: int = 78) -> float:
    base = EXPECTED_HR.get(ACTIVITY_INTENSITY.get(activity, 2), 75)
    return base - max(0, (age - 40) * 0.15)


def evaluate(reading: dict, thresholds: dict, patient: dict) -> list[dict]:
    """
    Return a list of detected conditions for one reading:
    [{type, severity, title, readings}, ...]
    """
    events: list[dict] = []
    hr = reading["heart_rate"]
    spo2 = reading["spo2"]
    temp = reading["temperature"]
    gsr = reading["gsr"]
    hrv = reading["hrv"]
    accel = reading.get("accel_mag", 1.0)
    gyro = reading.get("gyro_mag", 0.0)
    activity = reading.get("activity", "Resting")
    stress = stress_score(gsr, hrv)
    reading["stress_score"] = stress

    exp = expected_hr(activity, patient.get("age", 78))
    ctx = {
        **{k: reading.get(k) for k in (
            "heart_rate", "spo2", "temperature", "gsr", "hrv",
            "accel_mag", "gyro_mag", "activity", "steps")},
        "stress": stress,
        "hr_expected": exp,
        "spo2_safe": thresholds.get("spo2_low", 92),
        "temp_safe": thresholds.get("temp_high", 37.8),
        "hr_safe": thresholds.get("hr_high", 110),
        "hr_low_safe": thresholds.get("hr_low", 50),
    }

    # ── Fall Detection (highest priority) ────────────────────────────────
    if thresholds.get("fall_enabled", 1) and accel >= thresholds.get("fall_accel", 2.8) and gyro >= 2.4:
        events.append({
            "type": "Fall Detected",
            "severity": "critical",
            "title": "Fall detected — impact signature",
            "readings": ctx,
        })

    # ── Low Oxygen ───────────────────────────────────────────────────────
    if spo2 < thresholds.get("spo2_low", 92):
        sev = "critical" if spo2 <= thresholds.get("spo2_low", 92) - 3 else "high"
        events.append({
            "type": "Low Oxygen",
            "severity": sev,
            "title": f"Low blood oxygen — {spo2:.0f}%",
            "readings": ctx,
        })

    # ── Fever ────────────────────────────────────────────────────────────
    if temp >= thresholds.get("temp_high", 37.8):
        sev = "high" if temp >= thresholds.get("temp_high", 37.8) + 0.7 else "medium"
        events.append({
            "type": "Fever",
            "severity": sev,
            "title": f"Fever — {temp:.1f}°C",
            "readings": ctx,
        })
    elif temp <= thresholds.get("temp_low", 35.5):
        events.append({
            "type": "Fever",
            "severity": "medium",
            "title": f"Low body temperature — {temp:.1f}°C",
            "readings": ctx,
        })

    # ── Stress / Panic ───────────────────────────────────────────────────
    if stress >= 0.72 and hr - exp >= 30:
        events.append({
            "type": "Panic Attack",
            "severity": "critical",
            "title": f"Panic episode — stress {stress:.2f}",
            "readings": ctx,
        })
    elif stress >= thresholds.get("stress_high", 0.60):
        sev = "high" if stress >= 0.75 else "medium"
        events.append({
            "type": "High Stress",
            "severity": sev,
            "title": f"High stress — index {stress:.2f}",
            "readings": ctx,
        })

    # ── Heart-rate bounds ────────────────────────────────────────────────
    if hr >= thresholds.get("hr_high", 110) + 25:
        events.append({
            "type": "Tachycardia",
            "severity": "high",
            "title": f"Severe tachycardia — {hr:.0f} bpm",
            "readings": ctx,
        })
    elif hr >= thresholds.get("hr_high", 110):
        events.append({
            "type": "Tachycardia",
            "severity": "medium",
            "title": f"Elevated heart rate — {hr:.0f} bpm",
            "readings": ctx,
        })
    elif hr <= thresholds.get("hr_low", 50):
        events.append({
            "type": "Bradycardia",
            "severity": "high" if hr <= thresholds.get("hr_low", 50) - 6 else "medium",
            "title": f"Low heart rate — {hr:.0f} bpm",
            "readings": ctx,
        })

    # ── Fatigue (low HRV) ────────────────────────────────────────────────
    if hrv <= thresholds.get("hrv_low", 20) and stress < thresholds.get("stress_high", 0.6):
        events.append({
            "type": "Fatigue",
            "severity": "low",
            "title": f"Fatigue marker — HRV {hrv:.0f} ms",
            "readings": ctx,
        })

    return events


def inactivity_event(inactive_minutes: int, patient: dict) -> dict:
    ctx = {"inactive_minutes": inactive_minutes}
    return {
        "type": "Inactivity",
        "severity": "medium" if inactive_minutes < 180 else "high",
        "title": f"No movement for {inactive_minutes} minutes",
        "readings": ctx,
    }


def event_alert_payload(event: dict, patient: dict, lat: float | None, lng: float | None) -> dict:
    """Shape a detected event into an alert row (explanation added by caller)."""
    return {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": event["type"],
        "severity": event["severity"],
        "status": "active",
        "title": event["title"],
        "readings": event.get("readings", {}),
        "lat": lat,
        "lng": lng,
    }

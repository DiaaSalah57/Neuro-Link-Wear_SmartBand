"""
NeuroLink Wear — anomaly detection engine.

Real-time rule/ensemble detection for the four flagship conditions
(High Stress, Fever, Low Oxygen, Fall Detection) plus tachycardia,
bradycardia, fatigue and inactivity. Thresholds are per-patient and fully
editable from the dashboard's Management view.

Two-tier triggering (calibration-based AI, no training dataset):
  * clinical rules  — population/clinical thresholds (pipeline.py parity)
  * personal σ-gates — z-scores vs the wearer's CALIBRATED baselines
    (app/calibration.py + app/equations.py). A condition fires when EITHER
    tier fires, so personalisation can only ever ADD sensitivity — it can
    never make a clinically obvious event safe to ignore.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import equations as eq

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
    if hrv <= 0:
        return round(max(0.0, min(1.0, gsr_part)), 3)
    hrv_part = 1 - (hrv - HRV_MIN) / (HRV_MAX - HRV_MIN + 1e-6)
    return round(max(0.0, min(1.0, (gsr_part + hrv_part) / 2)), 3)


def expected_hr(activity: str, age: int = 78) -> float:
    base = EXPECTED_HR.get(ACTIVITY_INTENSITY.get(activity, 2), 75)
    return base - max(0, (age - 40) * 0.15)


def evaluate(reading: dict, thresholds: dict, patient: dict, cal: dict | None = None) -> list[dict]:
    """
    Return a list of detected conditions for one reading:
    [{type, severity, title, readings}, ...]

    ``cal`` is the patient's calibration state (app/calibration.py); when
    omitted, population priors are used and only the clinical tier runs.
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

    # ── calibrated equation layer (personal σ-evidence) ──────────────────
    cal = cal or {}
    baselines = cal.get("baselines", {})
    rules = {**eq.PERSONAL_RULE_DEFAULTS, **(cal.get("personal_rules") or {})}
    s_eq = eq.stress_index(gsr, hrv, hr, baselines, activity)
    f_eq = eq.fever_score(temp, hr, baselines, cal.get("temp_prev"))
    m_eq = eq.hr_mismatch(hr, activity, patient.get("age", 78), baselines)
    core_temp = f_eq["core_temp"]
    spo2_calibrated = spo2 + baselines.get("spo2_offset", 0.0)
    burden = cal.get("hypoxic_burden", 0.0)
    cal_stress_fire = s_eq["z_max"] >= rules["stress_z"]
    cal_fever_fire = core_temp >= eq.CLINICAL_FLOORS["temp_fever"]
    cal_hypoxia_fire = burden >= rules["hypoxic_burden_min"]
    cal_hr_fire = abs(m_eq["deviation"]) >= 35 and s_eq["z_max"] >= rules["stress_z"]

    exp = expected_hr(activity, patient.get("age", 78))
    ctx = {
        **{k: reading.get(k) for k in (
            "heart_rate", "spo2", "temperature", "gsr", "hrv",
            "accel_mag", "gyro_mag", "activity", "steps")},
        "stress": stress,
        "stress_calibrated": s_eq["calibrated"],
        "stress_z_max": s_eq["z_max"],
        "stress_terms": s_eq["terms"],
        "core_temp": core_temp,
        "spo2_calibrated": spo2_calibrated,
        "hypoxic_burden": burden,
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

    # ── Low Oxygen (clinical floor OR accumulated personal burden) ──────
    if spo2 > 0 and (spo2 < thresholds.get("spo2_low", 92) or spo2_calibrated < eq.CLINICAL_FLOORS["spo2_low"] or cal_hypoxia_fire):
        sev = "critical" if min(spo2, spo2_calibrated) <= eq.CLINICAL_FLOORS["spo2_urgent"] else "high"
        events.append({
            "type": "Low Oxygen",
            "severity": sev,
            "title": f"Low blood oxygen — {spo2:.0f}%",
            "readings": ctx,
        })

    # ── Fever (skin rule OR calibrated core-equivalent temp) ─────────────
    if temp > 0 and (temp >= thresholds.get("temp_high", 37.8) or cal_fever_fire):
        sev = "high" if max(temp, core_temp) >= eq.CLINICAL_FLOORS["temp_fever"] + 0.7 else "medium"
        events.append({
            "type": "Fever",
            "severity": sev,
            "title": f"Fever — {temp:.1f}°C (core-equiv. {core_temp:.1f}°C)",
            "readings": ctx,
        })
    elif temp > 0 and temp <= thresholds.get("temp_low", 35.5):
        events.append({
            "type": "Fever",
            "severity": "medium",
            "title": f"Low body temperature — {temp:.1f}°C",
            "readings": ctx,
        })

    # ── Stress / Panic (legacy score OR personal σ-evidence) ─────────────
    if hr > 0 and ((stress >= 0.72 and hr - exp >= 30) or (cal_hr_fire and stress >= 0.60)):
        events.append({
            "type": "Panic Attack",
            "severity": "critical",
            "title": f"Panic episode — stress {stress:.2f}",
            "readings": ctx,
        })
    elif stress >= thresholds.get("stress_high", 0.60) or cal_stress_fire:
        sev = "high" if stress >= 0.75 or s_eq["z_max"] >= 3.5 else "medium"
        events.append({
            "type": "High Stress",
            "severity": sev,
            "title": f"High stress — index {max(stress, s_eq['calibrated'] if cal_stress_fire else 0):.2f}",
            "readings": ctx,
        })

    # ── Heart-rate bounds ────────────────────────────────────────────────
    if hr > 0 and hr >= thresholds.get("hr_high", 110) + 25:
        events.append({
            "type": "Tachycardia",
            "severity": "high",
            "title": f"Severe tachycardia — {hr:.0f} bpm",
            "readings": ctx,
        })
    elif hr > 0 and hr >= thresholds.get("hr_high", 110):
        events.append({
            "type": "Tachycardia",
            "severity": "medium",
            "title": f"Elevated heart rate — {hr:.0f} bpm",
            "readings": ctx,
        })
    elif hr > 0 and hr <= thresholds.get("hr_low", 50):
        events.append({
            "type": "Bradycardia",
            "severity": "high" if hr <= thresholds.get("hr_low", 50) - 6 else "medium",
            "title": f"Low heart rate — {hr:.0f} bpm",
            "readings": ctx,
        })

    # ── Fatigue (low HRV — clinical floor OR personal % drop) ───────────
    hrv_personal = baselines.get("hrv_rest", 42.0) * (1 - rules["hrv_drop_pct"] / 100.0)
    if hrv > 0 and (hrv <= thresholds.get("hrv_low", 20) or hrv <= hrv_personal) and stress < thresholds.get("stress_high", 0.6) and not cal_stress_fire:
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

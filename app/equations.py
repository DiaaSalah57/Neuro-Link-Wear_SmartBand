"""
NeuroLink Wear — physiological equation library (calibration-based AI).

Every health score here is a *documented, deterministic equation* — no
training dataset, no learned weights. Personal accuracy comes from
calibration (``app/calibration.py``): automatic baselining from the wearer's
own stream plus optional guided reference measurements (oral thermometer,
clinical pulse oximeter, resting HR/HRV).

Two-tier safety design
──────────────────────
* ``CLINICAL_FLOORS`` — absolute clinical limits taken from published
  guidelines. Calibration can NEVER move these; a personal baseline must
  never make SpO2 < 90 look safe.
* Personal rules — z-scores against the wearer's own calibrated baselines,
  the layer that adapts to each individual.

Every scorer returns a ``terms`` dict so alert explanations can cite the
actual equation contributions ("GSR phasic +2.2σ, RMSSD −1.8σ").
"""
from __future__ import annotations

import math

# ───────────────────────── two-tier thresholds ──────────────────────────
# Tier 1: clinical absolutes — never personalised, never calibrated away.
CLINICAL_FLOORS = {
    "spo2_urgent": 90.0,        # % — hypoxaemia emergency (guideline floor)
    "spo2_low": 92.0,           # % — clinically significant desaturation
    "temp_fever": 37.8,         # °C core-equivalent — fever definition
    "temp_hypothermia": 35.5,   # °C
    "hr_max_absolute": 140.0,   # bpm at rest — urgent tachycardia screen
    "hr_min_absolute": 38.0,    # bpm — urgent bradycardia screen
    "fall_impact_g": 2.8,       # g — fall impact signature
    "fall_free_fall_g": 0.5,    # g — free-fall phase upper bound
    "fall_gyro": 2.4,           # rad/s — tumbling signature
}

# Tier 2: personal-rule defaults (z-score gates) — calibration-editable.
PERSONAL_RULE_DEFAULTS = {
    "stress_z": 2.0,        # σ above personal baseline
    "fever_z": 2.5,         # °C-equivalent σ above personal baseline
    "hr_z": 2.5,            # σ above personal baseline
    "hrv_drop_pct": 40.0,   # % below personal HRV baseline
    "hypoxic_burden_min": 3.0,   # %·min of accumulated desaturation
}

# Population priors (literature constants) used as day-0 baselines until the
# wearer's own calibration converges. Age-78 female reference.
POPULATION_PRIORS = {
    "hr_rest": 72.0,          # bpm
    "hrv_rest": 42.0,         # ms (RMSSD-ish for late 70s)
    "gsr_tonic": 0.45,        # µS baseline electrodermal level
    "gsr_mad": 0.18,          # µS robust spread
    "temp_skin": 36.4,        # °C skin (forearm) resting
    "spo2_rest": 97.0,        # %
    "temp_gain": 1.0,         # core ≈ gain·skin + offset
    "temp_offset": 0.5,       # skin→core offset default (°C)
    "spo2_offset": 0.0,       # band SpO2 → clinical SpO2 correction
}


# ───────────────────────── robust statistics helpers ────────────────────

def robust_z(x: float, center: float, spread: float) -> float:
    """z-score with a robust spread (MAD-based). ~1.4826 makes MAD ≈ σ."""
    s = max(spread, 1e-6)
    return (x - center) / s


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def ewma(prev: float, x: float, alpha: float) -> float:
    return prev + alpha * (x - prev)


# ───────────────────────── electrodermal activity ───────────────────────

def eda_split(gsr: float, tonic_prev: float, alpha: float = 0.05) -> tuple[float, float]:
    """
    Decompose skin conductance into tonic (SCL) and phasic (SCR) parts.

    Tonic level tracks hydration/temperature and drifts slowly; the phasic
    component (GSR − SCL) is the sympathetic-arousal signal that stress
    equations should use.
    """
    tonic = ewma(tonic_prev, gsr, alpha) if tonic_prev else gsr
    phasic = max(0.0, gsr - tonic)
    return round(tonic, 4), round(phasic, 4)


# ───────────────────────── stress index ─────────────────────────────────

def stress_index(gsr: float, hrv: float, hr: float, cal: dict, activity: str = "Resting") -> dict:
    """
    Calibrated stress index — 0.5 at the wearer's personal baseline.

    terms:
      gsr_ph    — phasic skin conductance vs personal tonic noise (↑ stress)
      hrv_drop  — HRV below personal resting baseline (↓ HRV = ↑ stress)
      hr_rise   — HR above personal resting baseline, counted only while
                  resting (a racing heart while walking is normal)

    ``z_max`` is the evidence gate the detection engine uses (personal rule,
    default ≥ 2σ). ``legacy`` reproduces the population-bounded
    pipeline.py score so day-one behaviour matches the offline pipeline.
    """
    tonic = cal.get("gsr_tonic", POPULATION_PRIORS["gsr_tonic"])
    gsr_mad = cal.get("gsr_mad", POPULATION_PRIORS["gsr_mad"])
    hrv_rest = cal.get("hrv_rest", POPULATION_PRIORS["hrv_rest"])
    hr_rest = cal.get("hr_rest", POPULATION_PRIORS["hr_rest"])

    _, phasic = eda_split(gsr, tonic)
    z_gsr = robust_z(phasic, 0.0, max(gsr_mad, 0.25))       # ≥0.25µS noise floor
    z_hrv = robust_z(hrv_rest - hrv, 0.0, max(hrv_rest * 0.25, 8.0)) if hrv > 0 else 0.0
    z_hr = robust_z(hr - hr_rest, 0.0, max(hr_rest * 0.20, 12.0)) if hr > 0 else 0.0
    resting = activity in ("Resting", "Sleeping", "")

    terms = {
        "gsr_phasic_z": round(z_gsr, 2),
        "hrv_drop_z": round(z_hrv, 2),
        "hr_rise_z": round(z_hr, 2),
        "resting": resting,
    }
    # 0.5 at baseline; σ-evidence pushes upward; HR only counts at rest.
    evidence = max(z_gsr, 0.0) + max(z_hrv, 0.0) + (max(z_hr, 0.0) if resting else 0.0)
    s = clamp(0.5 + evidence / 5.0)

    # legacy population-bounded score (pipeline.py parity)
    gsr_part = (gsr - 0.10) / (19.93 - 0.10 + 1e-6)
    if hrv > 0:
        hrv_part = 1 - (hrv - 13.60) / (89.96 - 13.60 + 1e-6)
        legacy = clamp((gsr_part + hrv_part) / 2)
    else:
        legacy = clamp(gsr_part)

    z_max = round(max(z_gsr, z_hrv, z_hr if resting else z_gsr), 2)
    return {
        "index": round(max(legacy, s if z_max >= 2.0 else 0.0), 3),
        "calibrated": round(s, 3),
        "legacy": round(legacy, 3),
        "z_max": z_max,
        "terms": terms,
    }


# ───────────────────────── fever / core temperature ─────────────────────

def core_temp_estimate(temp_skin: float, cal: dict) -> float:
    """
    Core-equivalent temperature from skin reading:

        T_core ≈ gain · T_skin + offset

    ``gain``/``offset`` are personal — calibrated by a single guided oral
    measurement (offset = T_oral − gain·T_skin_at_that_moment).
    """
    gain = cal.get("temp_gain", POPULATION_PRIORS["temp_gain"])
    offset = cal.get("temp_offset", POPULATION_PRIORS["temp_offset"])
    return round(gain * temp_skin + offset, 2)


def fever_score(temp_skin: float, hr: float, cal: dict, temp_prev: float | None = None,
                minutes: float = 2.0) -> dict:
    """
    Fever evidence from three independent equations (triangulation):
      core      — calibrated core-equivalent temperature vs 37.8 °C
      slope     — rate of rise (°C/h): >0.4 °C/h is a rising-fever signature
      coupling  — HR should rise ~7–10 bpm per 1 °C; check consistency
    """
    core = core_temp_estimate(temp_skin, cal)
    terms = {"core_temp": core}
    score = 0.0

    if core >= CLINICAL_FLOORS["temp_fever"]:
        score += 0.6
        terms["core_term"] = round(core - CLINICAL_FLOORS["temp_fever"], 2)
    elif core >= 37.4:
        score += 0.25
        terms["core_term"] = round(core - 37.4, 2)

    if temp_prev is not None and minutes > 0:
        rate = (temp_skin - temp_prev) * 60.0 / minutes   # °C/h
        terms["slope_c_per_h"] = round(rate, 2)
        if rate >= 0.4:
            score += 0.25
    hr_rest = cal.get("hr_rest", POPULATION_PRIORS["hr_rest"])
    if core >= 37.4 and hr >= hr_rest + 10:
        score += 0.15
        terms["hr_coupling"] = round(hr - hr_rest, 1)

    return {"score": round(clamp(score), 2), "core_temp": core, "terms": terms}


# ───────────────────────── hypoxic burden ───────────────────────────────

def hypoxic_burden_update(prev_burden: float, spo2: float, minutes: float = 2.0) -> float:
    """
    Accumulated desaturation load ( %·min ):

        B ← decay·B + minutes · max(0, 92 − SpO2)

    A single noisy 91 % sample is not an emergency; sustained desaturation
    is. Motion artifacts should be rejected upstream via the IMU gate.
    """
    depth = max(0.0, CLINICAL_FLOORS["spo2_low"] - spo2)
    return round(max(0.0, prev_burden * 0.85 + minutes * depth), 2)


# ───────────────────────── heart-rate fitness model ────────────────────

ACTIVITY_INTENSITY = {"Sleeping": 1, "Resting": 2, "Walking": 3, "Running": 4, "Exercising": 5}
EXPECTED_HR = {1: 62, 2: 75, 3: 100, 4: 155, 5: 145}


def expected_hr(activity: str, age: int, cal: dict) -> float:
    """
    Expected HR for an activity, anchored on the wearer's *calibrated*
    resting HR instead of a population constant:
        HR_exp = HR_rest_personal + (population_activity − population_resting)·age_factor
    """
    base = EXPECTED_HR.get(ACTIVITY_INTENSITY.get(activity, 2), 75)
    age_factor = max(0.55, 1.0 - max(0, age - 40) * 0.004)
    hr_rest = cal.get("hr_rest", POPULATION_PRIORS["hr_rest"])
    return round(hr_rest + (base - 75) * age_factor, 1)


def hr_mismatch(hr: float, activity: str, age: int, cal: dict) -> dict:
    """Chronotropic check — HR should track activity; big gaps are suspicious."""
    exp = expected_hr(activity, age, cal)
    return {"hr_expected": exp, "deviation": round(hr - exp, 1)}


# ───────────────────────── fall physics (for explanations) ─────────────

def fall_signature(accel: float, gyro: float, still: bool = False) -> dict:
    """
    Four-stage physical fall signature (state-machine style):
      free-fall → impact → tumbling → stillness.
    The live rule (detection.py) fires on impact+tumble; the stages are
    reported so explanations can describe what the IMU actually saw.
    """
    f = CLINICAL_FLOORS
    return {
        "impact": accel >= f["fall_impact_g"],
        "tumble": gyro >= f["fall_gyro"],
        "free_fall_possible": accel <= f["fall_free_fall_g"] + 0.5,
        "stillness": bool(still),
        "impact_g": round(accel, 2),
        "gyro_rad_s": round(gyro, 2),
    }

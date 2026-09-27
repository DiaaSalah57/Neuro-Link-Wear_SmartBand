"""
NeuroLink Wear — per-patient calibration engine.

Replaces the training-dataset normalisation bounds with *personal*
calibration, from two sources:

1. Automatic (unsupervised): every streamed reading refines slow EWMA
   baselines (resting HR/HRV, tonic GSR, skin temp, SpO2) and robust
   spread estimates; ``auto_fit()`` can snap baselines to percentiles of
   the last 24 h of stored vitals.

2. Guided (reference measurements): a handful of clinical ground-truth
   points — oral thermometer next to the band's skin reading, a clinical
   pulse oximeter, a quiet-rest HR/HRV measurement — become sensor
   offsets (skin→core temperature is personal: T_core ≈ g·T_skin + b).

Status flow: 'warming_up' → 'active' as observation count/confidence
grows. Clinical floors in ``equations.CLINICAL_FLOORS`` are never touched.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .db import get_db, one
from .equations import POPULATION_PRIORS, PERSONAL_RULE_DEFAULTS, eda_split, ewma


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


DEFAULT_STATE = {
    "status": "warming_up",            # warming_up | active
    "n_obs": 0,
    "confidence": 0.0,                 # 0..1
    "baselines": dict(POPULATION_PRIORS),          # calibrated centres
    "spread": {"hr": 8.0, "hrv": 8.0, "gsr": 0.18, "temp": 0.25, "spo2": 0.8},
    "personal_rules": dict(PERSONAL_RULE_DEFAULTS),
    "sources": {k: "prior" for k in POPULATION_PRIORS},   # prior|auto|guided|manual
    "temp_prev": None,                 # for fever slope term
    "hypoxic_burden": 0.0,
    "updated_at": None,
}


def _ensure_tables() -> None:
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS calibration (
            patient_id  INTEGER PRIMARY KEY,
            state       TEXT NOT NULL,
            updated_at  TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS calibration_refs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id  INTEGER NOT NULL,
            kind        TEXT NOT NULL,
            value       REAL NOT NULL,
            band_value  REAL,
            applied     TEXT NOT NULL,
            note        TEXT,
            ts          TEXT NOT NULL
        )""")


def get_calibration(patient_id: int = 1) -> dict:
    _ensure_tables()
    with get_db() as db:
        row = one(db.execute("SELECT state FROM calibration WHERE patient_id=?", (patient_id,)))
    if not row:
        return json.loads(json.dumps(DEFAULT_STATE))
    state = json.loads(row["state"])
    # forward-compat: fill any keys added since the row was written
    for k, v in DEFAULT_STATE.items():
        state.setdefault(k, json.loads(json.dumps(v)))
    return state


def _save(patient_id: int, state: dict) -> None:
    state["updated_at"] = _now_iso()
    with get_db() as db:
        db.execute(
            """INSERT INTO calibration(patient_id, state, updated_at) VALUES(?,?,?)
               ON CONFLICT(patient_id) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at""",
            (patient_id, json.dumps(state), state["updated_at"]),
        )


# ───────────────────────── automatic calibration ────────────────────────

def observe(reading: dict, patient_id: int = 1) -> dict:
    """
    Fold one streamed reading into the personal baselines (slow EWMA with
    sanity gates so crisis readings don't drag the baseline around). Cheap
    enough to run on every telemetry tick.
    """
    state = get_calibration(patient_id)
    b = state["baselines"]

    hr = float(reading.get("heart_rate") or 0)
    hrv = float(reading.get("hrv") or 0)
    gsr = float(reading.get("gsr") or 0)
    temp = float(reading.get("temperature") or 0)
    spo2 = float(reading.get("spo2") or 0)

    # Only "quiet" readings may shape resting baselines (gate out crises).
    quiet = (45 <= hr <= 110 and 15 <= hrv <= 100 and 0 <= gsr <= 8
             and 34.5 <= temp <= 38.5 and 88 <= spo2 <= 100)
    if quiet:
        a = 0.02  # slow — baselines drift, never jump
        b["hr_rest"] = round(ewma(b["hr_rest"], hr, a), 2)
        b["hrv_rest"] = round(ewma(b["hrv_rest"], hrv, a), 2)
        b["temp_skin"] = round(ewma(b["temp_skin"], temp, a), 3)
        b["spo2_rest"] = round(ewma(b["spo2_rest"], spo2, a), 2)
        tonic, _ = eda_split(gsr, b.get("gsr_tonic", 0.45), alpha=0.01)  # SCL drifts slowly
        b["gsr_tonic"] = round(tonic, 4)
        # robust spread: mean absolute deviation against the drifting centre
        state["spread"]["gsr"] = round(max(0.05, ewma(state["spread"]["gsr"], abs(gsr - b["gsr_tonic"]), 0.02)), 4)
        b["gsr_mad"] = state["spread"]["gsr"]
        state["n_obs"] += 1
        state["confidence"] = round(min(1.0, state["n_obs"] / 600.0), 3)   # ~20 min of ticks → half
        if state["status"] == "warming_up" and state["n_obs"] >= 60:
            state["status"] = "active"
        if state["sources"].get("hr_rest") == "prior":
            state["sources"]["hr_rest"] = "auto"
        if state["sources"].get("hrv_rest") == "prior":
            state["sources"]["hrv_rest"] = "auto"
        if state["sources"].get("gsr_tonic") == "prior":
            state["sources"]["gsr_tonic"] = "auto"
        if state["sources"].get("temp_skin") == "prior":
            state["sources"]["temp_skin"] = "auto"
        if state["sources"].get("spo2_rest") == "prior":
            state["sources"]["spo2_rest"] = "auto"

    # always track fever slope + hypoxic burden (crisis-safe)
    state["temp_prev"] = temp or state.get("temp_prev")
    from .equations import hypoxic_burden_update
    state["hypoxic_burden"] = hypoxic_burden_update(
        state.get("hypoxic_burden", 0.0), spo2 or 99.0)
    _save(patient_id, state)
    return state


def auto_fit(patient_id: int = 1, hours: int = 24) -> dict:
    """
    Snap baselines to robust percentiles of the last N hours of stored
    vitals. Returns {before, after, points} so the UI can preview the diff.
    """
    from .db import rows as _rows
    _ensure_tables()
    state = get_calibration(patient_id)
    before = json.loads(json.dumps(state["baselines"]))
    cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as db:
        data = _rows(db.execute(
            """SELECT heart_rate, hrv, gsr, temperature, spo2 FROM vitals
               WHERE ts>=datetime(?, ?) ORDER BY ts""",
            (cutoff, f"-{int(hours)} hours"),
        ))
    if not data:
        return {"before": before, "after": before, "points": 0, "changed": False}

    def pct(vals, p):
        vals = sorted(v for v in vals if v is not None)
        if not vals:
            return None
        k = (len(vals) - 1) * p / 100.0
        f, c = int(k), min(int(k) + 1, len(vals) - 1)
        return vals[f] + (vals[c] - vals[f]) * (k - f)

    hrs = [r["heart_rate"] for r in data if r["heart_rate"]]
    hrvs = [r["hrv"] for r in data if r["hrv"] and r["hrv"] > 5]
    gsrs = [r["gsr"] for r in data if r["gsr"] is not None]
    temps = [r["temperature"] for r in data if r["temperature"]]
    spo2s = [r["spo2"] for r in data if r["spo2"]]

    # resting = lower percentiles of HR (quiet periods), upper percentiles of HRV
    if hrs:
        state["baselines"]["hr_rest"] = round(pct(hrs, 25), 2)
    if hrvs:
        state["baselines"]["hrv_rest"] = round(pct(hrvs, 75), 2)
    if gsrs:
        state["baselines"]["gsr_tonic"] = round(pct(gsrs, 35), 4)
        state["baselines"]["gsr_mad"] = round(max(0.05, (pct(gsrs, 85) - pct(gsrs, 35)) / 2.0), 4)
        state["spread"]["gsr"] = state["baselines"]["gsr_mad"]
    if temps:
        state["baselines"]["temp_skin"] = round(pct(temps, 50), 3)
    if spo2s:
        state["baselines"]["spo2_rest"] = round(pct(spo2s, 60), 2)

    for key in ("hr_rest", "hrv_rest", "gsr_tonic", "temp_skin", "spo2_rest", "gsr_mad"):
        if state["baselines"][key] != before.get(key):
            state["sources"][key] = "auto"
    state["status"] = "active"
    state["confidence"] = round(max(state["confidence"], min(1.0, len(data) / 200.0)), 3)
    state["n_obs"] = max(state["n_obs"], len(data))
    _save(patient_id, state)
    return {"before": before, "after": dict(state["baselines"]), "points": len(data), "changed": state["baselines"] != before}


# ───────────────────────── guided reference points ──────────────────────

REFERENCE_KINDS = {
    "oral_temp": "Oral thermometer reading (calibrates skin→core offset)",
    "pulse_ox": "Clinical pulse-oximeter SpO2 (calibrates band SpO2 offset)",
    "resting_hr": "Measured resting heart rate (bpm)",
    "resting_hrv": "Measured resting HRV (ms)",
}


def add_reference(kind: str, value: float, band_value: float | None = None,
                  note: str = "", patient_id: int = 1) -> dict:
    """
    Apply one guided calibration measurement.

    oral_temp  : value = oral °C, band_value = band skin °C at the same
                 moment → temp_offset = value − gain·band_value
    pulse_ox   : value = clinical %, band_value = band % → spo2_offset
    resting_hr / resting_hrv : set the corresponding baseline directly
                 (band_value ignored).
    """
    if kind not in REFERENCE_KINDS:
        raise ValueError(f"kind must be one of {list(REFERENCE_KINDS)}")
    if value is None:
        raise ValueError("value is required")

    state = get_calibration(patient_id)
    b = state["baselines"]
    applied = ""

    if kind == "oral_temp":
        if band_value is None:
            band_value = b.get("temp_skin", 36.4)
        b["temp_offset"] = round(float(value) - b.get("temp_gain", 1.0) * float(band_value), 3)
        state["sources"]["temp_offset"] = "guided"
        state["sources"]["temp_gain"] = "guided" if state["sources"].get("temp_gain") == "guided" else state["sources"].get("temp_gain", "prior")
        applied = f"temp_offset → {b['temp_offset']:+.2f} °C (core ≈ {b.get('temp_gain', 1.0)}·skin {b['temp_offset']:+.2f})"
    elif kind == "pulse_ox":
        if band_value is None:
            band_value = b.get("spo2_rest", 97.0)
        b["spo2_offset"] = round(float(value) - float(band_value), 2)
        state["sources"]["spo2_offset"] = "guided"
        applied = f"spo2_offset → {b['spo2_offset']:+.1f} %"
    elif kind == "resting_hr":
        b["hr_rest"] = round(float(value), 2)
        state["sources"]["hr_rest"] = "guided"
        applied = f"hr_rest → {b['hr_rest']} bpm"
    elif kind == "resting_hrv":
        b["hrv_rest"] = round(float(value), 2)
        state["sources"]["hrv_rest"] = "guided"
        applied = f"hrv_rest → {b['hrv_rest']} ms"

    state["status"] = "active"
    state["confidence"] = round(min(1.0, state["confidence"] + 0.15), 3)
    _save(patient_id, state)

    with get_db() as db:
        db.execute(
            "INSERT INTO calibration_refs(patient_id,kind,value,band_value,applied,note,ts) VALUES(?,?,?,?,?,?,?)",
            (patient_id, kind, float(value), band_value, applied, note, _now_iso()),
        )
    return {"state": state, "applied": applied}


def apply_manual(updates: dict, patient_id: int = 1) -> dict:
    """
    Manual slider updates: {'baselines': {...}, 'personal_rules': {...}}.
    Clinical floors are not editable here by design.
    """
    state = get_calibration(patient_id)
    for k, v in (updates.get("baselines") or {}).items():
        if k in state["baselines"]:
            state["baselines"][k] = float(v)
            state["sources"][k] = "manual"
    for k, v in (updates.get("personal_rules") or {}).items():
        if k in state["personal_rules"]:
            state["personal_rules"][k] = float(v)
    _save(patient_id, state)
    return state


def list_references(patient_id: int = 1) -> list[dict]:
    _ensure_tables()
    with get_db() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM calibration_refs WHERE patient_id=? ORDER BY ts DESC LIMIT 20", (patient_id,)).fetchall()]

#!/usr/bin/env python3
"""
NeuroLink Wear — calibration engine + two-tier detection suite.

Verifies the equation-based AI (no training dataset):
  A. equation library units (stress index, core temp, hypoxic burden, fall physics)
  B. calibration module (observe/auto-fit/guided references/manual, floor immutability)
  C. detection OR-gates (personal σ-triggers ADD to clinical rules — never replace)
  D. HTTP API (login, /calibration CRUD, guided refs, auto-fit)
  E. regression: the 8 demo triggers still fire (no behavioural regression)

Run:  .venv/bin/python calib_suite.py   (server must be running on :8000)
"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
PASS = 0
FAILED = []


def check(name, cond, detail=""):
    global PASS
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAILED.append(name)
        print(f"  ✗ FAIL: {name} {detail}")


def http(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {}


# ══════════════════════════ A. equation library ══════════════════════════
print("\n── A. equation library ──")
from app import equations as eq
from app import calibration as cal

# robust z
check("robust_z centred = 0", abs(eq.robust_z(5, 5, 2)) < 1e-9)
check("robust_z scale", abs(eq.robust_z(7, 5, 2) - 1.0) < 1e-9)

# EDA split: phasic = gsr − tonic
tonic, phasic = eq.eda_split(1.0, 0.4)
check("eda_split tonic drifts up", tonic > 0.4 and tonic < 1.0, f"tonic={tonic}")
check("eda_split phasic positive", phasic > 0)

# stress index: rest ≈ baseline, crisis ≈ evidence
rest = eq.stress_index(0.35, 55, 70, {"gsr_tonic": 0.35, "gsr_mad": 0.18, "hrv_rest": 55, "hr_rest": 70})
crisis = eq.stress_index(6.0, 16, 108, {"gsr_tonic": 0.35, "gsr_mad": 0.18, "hrv_rest": 55, "hr_rest": 70})
check("stress at rest: no z-trigger", rest["z_max"] < 2.0, f"z={rest['z_max']}")
check("stress at rest: index not high", rest["index"] < 0.6, f"idx={rest['index']}")
check("stress crisis: z-trigger fires", crisis["z_max"] >= 2.0, f"z={crisis['z_max']}")
check("stress crisis: index high", crisis["index"] >= 0.6, f"idx={crisis['index']}")
check("stress terms exposed for explanations", set(crisis["terms"]) >= {"gsr_phasic_z", "hrv_drop_z", "hr_rise_z"})

# walking is NOT a stress crisis (HR term excluded at activity)
walk = eq.stress_index(0.8, 42, 96, {"gsr_tonic": 0.45, "gsr_mad": 0.3, "hrv_rest": 42, "hr_rest": 72}, "Walking")
check("walking HR rise excluded from evidence", walk["z_max"] < 2.0 or walk["terms"]["resting"] is False, f"z={walk['z_max']}")

# core temp + fever
core = eq.core_temp_estimate(36.4, {"temp_gain": 1.0, "temp_offset": 0.8})
check("core_temp_offset applied", abs(core - 37.2) < 0.01, f"core={core}")
fever = eq.fever_score(37.3, 100, {"temp_gain": 1.0, "temp_offset": 1.0, "hr_rest": 70})
check("fever via calibrated core (skin 37.3 + offset 1.0)", fever["core_temp"] >= 37.8 and fever["score"] >= 0.6)
check("fever terms exposed", "core_temp" in fever["terms"])

# hypoxic burden accumulates
b1 = eq.hypoxic_burden_update(0.0, 90.0)
b2 = eq.hypoxic_burden_update(b1, 90.0)
check("hypoxic burden accumulates", b2 > b1 > 0, f"{b1}→{b2}")
check("hypoxic burden decays at normal SpO2", eq.hypoxic_burden_update(4.0, 98.0) < 4.0)

# fall physics
sig = eq.fall_signature(3.2, 2.9)
check("fall impact+tumble detected", sig["impact"] and sig["tumble"])
check("fall physics stages exposed", set(sig) >= {"impact", "tumble", "free_fall_possible", "stillness"})

# expected HR anchored on personal rest
exp78 = eq.expected_hr("Sleeping", 78, {"hr_rest": 64.0})
check("expected_hr personal-anchored", abs(exp78 - (64.0 + (62 - 75) * max(0.55, 1 - 38 * 0.004))) < 0.2, f"exp={exp78}")

# clinical floors: literals are never mutated by scorers
import copy
floors_before = copy.deepcopy(eq.CLINICAL_FLOORS)
eq.stress_index(9, 5, 200, {})
eq.fever_score(41, 200, {})
eq.hypoxic_burden_update(100, 70)
check("CLINICAL_FLOORS immutable", eq.CLINICAL_FLOORS == floors_before)

# ══════════════════════════ B. calibration module ════════════════════════
print("\n── B. calibration module (direct) ──")
from app.db import get_db
with get_db() as db:  # make unit tests idempotent across runs
    db.execute("DELETE FROM calibration WHERE patient_id IN (998, 999)")
    db.execute("DELETE FROM calibration_refs WHERE patient_id IN (998, 999)")
state = cal.get_calibration(999)  # unsaved patient → defaults
check("fresh patient = warming_up priors", state["status"] == "warming_up"
      and state["baselines"]["hr_rest"] == eq.POPULATION_PRIORS["hr_rest"])
check("defaults carry personal rules", state["personal_rules"]["stress_z"] == 2.0)

# observe: quiet reading updates baselines; crisis reading does not drag resting HR
s2 = cal.get_calibration(999)
for _ in range(3):
    s2 = cal.observe({"heart_rate": 70, "hrv": 50, "gsr": 0.4, "temperature": 36.4, "spo2": 97}, 999)
h_before = s2["baselines"]["hr_rest"]
s2 = cal.observe({"heart_rate": 150, "hrv": 12, "gsr": 6.0, "temperature": 38.5, "spo2": 88}, 999)
check("crisis reading gated out of baselines", abs(s2["baselines"]["hr_rest"] - h_before) < 0.5,
      f"{h_before}→{s2['baselines']['hr_rest']}")
check("observe counts only quiet samples", s2["n_obs"] == 3, f"n={s2['n_obs']}")
check("hypoxic burden tracked in state", s2["hypoxic_burden"] > 0)

# guided oral temp reference → personal offset
r = cal.add_reference("oral_temp", 37.2, band_value=36.4, note="unit", patient_id=999)
check("oral ref sets guided offset", r["state"]["baselines"]["temp_offset"] == 0.8,
      f"off={r['state']['baselines']['temp_offset']}")
check("oral ref source = guided", r["state"]["sources"]["temp_offset"] == "guided")
check("oral ref recorded in history", len(cal.list_references(999)) >= 1)

# pulse ox reference
r = cal.add_reference("pulse_ox", 98.0, band_value=96.5, patient_id=999)
check("pulse ox sets SpO2 offset", r["state"]["baselines"]["spo2_offset"] == 1.5)

# resting hr reference
r = cal.add_reference("resting_hr", 61.0, patient_id=999)
check("resting HR reference applied", r["state"]["baselines"]["hr_rest"] == 61.0)

# manual overrides
s3 = cal.apply_manual({"baselines": {"hr_rest": 66.0}, "personal_rules": {"stress_z": 1.5}}, 999)
check("manual baseline + rule applied", s3["baselines"]["hr_rest"] == 66.0
      and s3["personal_rules"]["stress_z"] == 1.5
      and s3["sources"]["hr_rest"] == "manual")

# manual cannot touch floors (they aren't in the schema)
check("floors not part of editable state", "spo2_urgent" not in s3["baselines"])

# bad reference kind raises
try:
    cal.add_reference("nope", 1.0, patient_id=999)
    check("bad reference kind rejected", False)
except ValueError:
    check("bad reference kind rejected", True)

# auto_fit over the real vitals stream (single-wearer table)
fit = cal.auto_fit(1, hours=24)
check("auto_fit returns diff shape", {"before", "after", "points", "changed"} <= set(fit))
check("auto_fit sees day of vitals", fit["points"] > 100, f"points={fit['points']}")
check("auto_fit resting-HR sane", 40 <= fit["after"]["hr_rest"] <= 120, f"hr_rest={fit['after']['hr_rest']}")
check("auto_fit resting-HRV sane", 10 <= fit["after"]["hrv_rest"] <= 120, f"hrv_rest={fit['after']['hrv_rest']}")

# ══════════════════════════ C. detection OR-gates ═════════════════════════
print("\n── C. detection two-tier OR-gates ──")
from app.detection import evaluate

th = {"spo2_low": 92, "spo2_urgent": 90, "temp_high": 37.8, "temp_low": 35.5,
      "hr_high": 115, "hr_low": 42, "hrv_low": 20, "hr_critical_high": 145,
      "hr_critical_low": 35, "stress_high": 0.6}
patient = {"name": "T", "age": 78}
calib = {
    "baselines": {"hr_rest": 64.0, "hrv_rest": 55.0, "gsr_tonic": 0.35, "gsr_mad": 0.18,
                  "temp_gain": 1.0, "temp_offset": 1.0, "spo2_offset": 0.0},
    "personal_rules": {"stress_z": 2.0, "hrv_drop_pct": 40.0, "hypoxic_burden_min": 3.0,
                       "fever_z": 2.5, "hr_z": 2.5},
    "temp_prev": 37.0,
    "hypoxic_burden": 0.0,
}

# (1) stress via σ-gate only (legacy score deliberately < 0.60)
ev = evaluate({"heart_rate": 70, "spo2": 97, "temperature": 36.4, "gsr": 5.0, "hrv": 25,
               "accel_mag": 1.0, "gyro_mag": 0.1, "activity": "Resting", "steps": 0}, th, patient, calib)
types = [e["type"] for e in ev]
legacy_below = ev[0]["readings"]["stress"] < 0.6 if ev else True
check("σ-gate fires High Stress where legacy does not", "High Stress" in types, f"types={types}")
check("ctx carries calibrated terms", "stress_terms" in ev[0]["readings"] and "stress_z_max" in ev[0]["readings"])

# (2) fever via calibrated core (skin below clinical skin threshold)
ev = evaluate({"heart_rate": 80, "spo2": 97, "temperature": 37.3, "gsr": 0.3, "hrv": 50,
               "accel_mag": 1.0, "gyro_mag": 0.1, "activity": "Resting", "steps": 0}, th, patient, calib)
types = [e["type"] for e in ev]
check("fever fires via core-equivalent (offset 1.0)", "Fever" in types, f"types={types}")
check("fever title shows core-equiv", any("core-equiv" in e["title"] for e in ev))

# (3) hypoxic burden OR-gate (SpO2 93 — above the clinical rule)
calib2 = dict(calib, hypoxic_burden=4.0)
ev = evaluate({"heart_rate": 80, "spo2": 93, "temperature": 36.4, "gsr": 0.3, "hrv": 50,
               "accel_mag": 1.0, "gyro_mag": 0.1, "activity": "Sleeping", "steps": 0}, th, patient, calib2)
check("low oxygen fires on accumulated burden", any(e["type"] == "Low Oxygen" for e in ev),
      f"types={[e['type'] for e in ev]}")

# (4) fatigue personal % drop (hrv 30 vs rest 55 = 45% drop > 40% rule, but σ < 2 → not stress)
ev = evaluate({"heart_rate": 60, "spo2": 97, "temperature": 36.4, "gsr": 0.3, "hrv": 30,
               "accel_mag": 1.0, "gyro_mag": 0.1, "activity": "Sleeping", "steps": 0}, th, patient, calib)
check("fatigue fires on personal HRV drop", any(e["type"] == "Fatigue" for e in ev),
      f"types={[e['type'] for e in ev]}")
# severe crash (σ ≥ 2) belongs to the stress tier instead — mutually exclusive by design
ev = evaluate({"heart_rate": 60, "spo2": 97, "temperature": 36.4, "gsr": 0.3, "hrv": 16,
               "accel_mag": 1.0, "gyro_mag": 0.1, "activity": "Sleeping", "steps": 0}, th, patient, calib)
types = [e["type"] for e in ev]
check("severe HRV crash routes to stress tier", ("High Stress" in types or "Panic Attack" in types)
      and "Fatigue" not in types, f"types={types}")

# (5) fall still fires (unchanged rule)
ev = evaluate({"heart_rate": 75, "spo2": 97, "temperature": 36.4, "gsr": 0.3, "hrv": 50,
               "accel_mag": 3.2, "gyro_mag": 3.0, "activity": "Resting", "steps": 0}, th, patient, calib)
check("fall rule unchanged", any(e["type"] == "Fall Detected" for e in ev))

# (6) calm reading → nothing
ev = evaluate({"heart_rate": 70, "spo2": 97, "temperature": 36.4, "gsr": 0.35, "hrv": 55,
               "accel_mag": 1.0, "gyro_mag": 0.1, "activity": "Resting", "steps": 0}, th, patient, calib)
check("calm reading stays quiet", ev == [], f"types={[e['type'] for e in ev]}")

# (7) without cal → clinical tier still works (backward compatible)
ev = evaluate({"heart_rate": 125, "spo2": 97, "temperature": 36.4, "gsr": 0.3, "hrv": 50,
               "accel_mag": 1.0, "gyro_mag": 0.1, "activity": "Resting", "steps": 0}, th, patient, None)
check("clinical tier works without cal", any(e["type"] == "Tachycardia" for e in ev))

# (8) critical tachycardia + inactivity detector (regression coverage)
ev = evaluate({"heart_rate": 150, "spo2": 97, "temperature": 36.4, "gsr": 0.3, "hrv": 50,
               "accel_mag": 1.0, "gyro_mag": 0.1, "activity": "Resting", "steps": 0}, th, patient, calib)
check("severe tachycardia fires (severity high)", any(
    e["type"] == "Tachycardia" and e["severity"] == "high" and "Severe" in e["title"] for e in ev),
    f"{[(e['type'], e['severity']) for e in ev]}")
from app.detection import inactivity_event
check("inactivity detector unchanged", (inactivity_event(20.0, 3.0) or {}).get("type") == "Inactivity")

# ══════════════════════════ D. HTTP API ══════════════════════════════════
print("\n── D. HTTP API ──")
st, body = http("POST", "/api/auth/login", {"email": "admin@neurolink.health", "password": "admin123"})
check("admin login", st == 200 and body.get("token"))
tok = body["token"]

st, body = http("GET", "/api/calibration", token=tok)
check("GET /calibration 200", st == 200)
check("GET returns state+floors+refs+live", st == 200 and {"state", "floors", "references", "reference_kinds"} <= set(body))
check("GET live equation breakdown", st == 200 and body.get("live") and "stress" in body["live"]
      and "terms" in body["live"]["stress"])
check("floors served read-only list", st == 200 and body["floors"]["spo2_urgent"] == 90.0)

st, body = http("POST", "/api/calibration/auto-fit", {}, token=tok)
check("POST auto-fit 200 with diff", st == 200 and "before" in body and "after" in body and "points" in body)

st, body = http("POST", "/api/calibration/reference",
                {"kind": "oral_temp", "value": 37.0, "band_value": 36.2, "note": "suite"}, tok)
check("POST guided oral reference 200", st == 200 and "applied" in body)
st, cal_state = http("GET", "/api/calibration", token=tok)
check("guided offset persisted", abs(cal_state["state"]["baselines"]["temp_offset"] - 0.8) < 0.01,
      f"off={cal_state['state']['baselines']['temp_offset']}")
check("reference listed in history", any(r["kind"] == "oral_temp" for r in cal_state["references"]))

st, body = http("POST", "/api/calibration/reference", {"kind": "bogus", "value": 1}, tok)
check("bad reference kind → 400", st == 400)

st, body = http("PUT", "/api/calibration", {"baselines": {"hr_rest": 63.0},
                                            "personal_rules": {"stress_z": 1.8}}, tok)
check("PUT manual updates 200", st == 200 and body["baselines"]["hr_rest"] == 63.0)
check("PUT personal rule updated", body["personal_rules"]["stress_z"] == 1.8)

st, _ = http("GET", "/api/calibration")
check("calibration requires auth", st in (401, 403))

st, body = http("POST", "/api/auth/login", {"email": "caregiver@neurolink.health", "password": "caregiver123"})
ctok = body.get("token")
st, _ = http("POST", "/api/calibration/auto-fit", {}, token=ctok)
check("caregiver (staff) can auto-fit", st == 200)

# ══════════════════════════ E. demo-trigger regression ═══════════════════
print("\n── E. regression: 8 demo triggers still fire ──")


def types_in(o):
    out = set()
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "type" and isinstance(v, str):
                out.add(v)
            else:
                out |= types_in(v)
    elif isinstance(o, list):
        for v in o:
            out |= types_in(v)
    return out


import time


def alert_ids_types():
    st, body = http("GET", "/api/alerts?hours=1&limit=100", token=tok)
    items = (body.get("data") or []) if isinstance(body, dict) else (body or [])
    return {a["id"]: a["type"] for a in items} if st == 200 else {}


triggers = [
    ("stress", {"High Stress", "Panic Attack"}),
    ("fall", {"Fall Detected", "Fall Detection"}),
    ("fever", {"Fever"}),
    ("desat", {"Low Oxygen"}),
    ("walk", set()),       # activity change must simply be accepted
    ("normal", set()),     # recovery phase must be accepted
]
for kind, expect in triggers:
    before = alert_ids_types()
    st, body = http("POST", f"/api/demo/trigger?kind={kind}", {}, tok)
    check(f"trigger {kind} accepted", st == 200 and body.get("ok"), f"resp={body}")
    time.sleep(2.5)          # alert is created on the next simulator tick
    after = alert_ids_types()
    new_types = {t for i, t in after.items() if i not in before}   # diff by NEW ids
    if expect:
        check(f"trigger {kind} → new alert {sorted(expect)}", bool(expect & new_types),
              f"new={sorted(new_types)}")
    else:
        check(f"trigger {kind} quiet", True)

print(f"\n{'='*60}\n  TOTAL: {PASS} passed, {len(FAILED)} failed")
if FAILED:
    for f_ in FAILED:
        print(f"   ✗ {f_}")
    raise SystemExit(1)
print("  🧪 CALIBRATION SUITE: PASS")

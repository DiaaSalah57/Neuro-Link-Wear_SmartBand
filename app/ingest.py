"""
NeuroLink Wear — shared device-ingest pipeline.

One processing path for every reading that arrives from real hardware,
whether it came through ``POST /api/telemetry/ingest`` or through the
MQTT bridge (``app/mqtt.py``): normalise → detect → explain → persist →
broadcast. Keeping a single path means a fall detected over MQTT gets
exactly the same AI explanation, severity and WebSocket fan-out as one
detected over REST.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .calibration import observe as cal_observe
from .db import get_db, one
from .detection import evaluate, stress_score
from .insights import now_iso
from .simulator import get_simulator


# ── ESP32 wire-format mapping (Smart_band/smart_band.ino — source of truth) ──
# The firmware publishes on ``neurolink/sensors/data`` every 60 s:
#   {ts, Heart_Rate, Body_Temperature, Blood_Oxygen, Step_Count, Activity_Status,
#    Accel_X/Y/Z [g], Gyro_X/Y/Z [rad/s], GSR_Value [µS], HRV [RMSSD ms],
#    Sweat_Response}
# Mapping rules (the firmware is never modified):
#   * 0-sentinels — Heart_Rate / HRV report 0.0 until the sensors have signal;
#     0 is never treated as a real vital (it would fire Bradycardia / HRV-drop
#     on the very first reading). Population-prior defaults stand in instead.
#   * GSR — the firmware's µS value is used as-is when it sits in the calibrated
#     band (0.10..19.93 — models/pipeline_stats.json, detection.GSR_MIN/MAX).
#     Its ADC transform (4095-adc)*0.025 can theoretically overshoot that band
#     (up to ~102 µS on wet electrodes); overshoot is mapped back into the band
#     with GSR_FIRMWARE_SCALE so the normalised stress index can't peg at 1.0.
#   * ts — GPS-derived UTC timestamp. Without a GPS fix the firmware falls back
#     to a FIXED date, so device timestamps outside a ±TS_WINDOW_H window of
#     "now" are replaced with server time (keeps history ordering honest).
#   * Accel [g] and Gyro [rad/s] match the fall thresholds (2.8 g impact,
#     2.4 rad/s rotation) — no conversion.
#   * lat/lng pass through when present (band GPS added later), else the
#     simulated home-base coordinates are used.

GSR_FIRMWARE_SCALE = 0.1   # overshoot guard: firmware ADC µS -> calibrated µS band
GSR_BAND_MAX = 20.0        # calibrated band ceiling (dataset max 19.93)
TS_WINDOW_H = 36.0         # accept device timestamps only within this window


def _first(d: dict, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _num(v, default: float, positive: bool = False) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if positive and f <= 0:
        return default
    return f


def _device_ts(d: dict) -> str:
    raw = _first(d, "ts", "timestamp")
    if raw is not None:
        try:
            t = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if abs((datetime.now(timezone.utc) - t).total_seconds()) <= TS_WINDOW_H * 3600:
                return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    return now_iso()


def build_reading(d: dict) -> dict:
    """Normalise an ESP32 / internal payload into the canonical reading shape."""
    sim = get_simulator()
    reading = {
        "ts": _device_ts(d),
        "heart_rate": _num(_first(d, "Heart_Rate", "heart_rate"), 0.0),
        "temperature": _num(_first(d, "Body_Temperature", "temperature"), 0.0),
        "spo2": _num(_first(d, "Blood_Oxygen", "spo2"), 0.0),
        "gsr": _num(_first(d, "GSR_Value", "gsr"), 0.0),
        "hrv": _num(_first(d, "HRV", "hrv"), 0.0),
        "steps": int(_num(_first(d, "Step_Count", "steps"), 0.0)),
        "activity": _first(d, "Activity_Status", "activity") or "Resting",
        "accel_x": _num(_first(d, "Accel_X", "accel_x"), 0.0),
        "accel_y": _num(_first(d, "Accel_Y", "accel_y"), 0.0),
        "accel_z": _num(_first(d, "Accel_Z", "accel_z"), 1.0),
        "gyro_x": _num(_first(d, "Gyro_X", "gyro_x"), 0.0),
        "gyro_y": _num(_first(d, "Gyro_Y", "gyro_y"), 0.0),
        "gyro_z": _num(_first(d, "Gyro_Z", "gyro_z"), 0.0),
        "sweat_response": _num(_first(d, "Sweat_Response", "sweat_response", "sweat"), 0.0),
        "battery": int(_num(_first(d, "battery", "Battery"), 100.0)),
        "charging": bool(d.get("charging", False)),
    }
    if reading["gsr"] > GSR_BAND_MAX:          # firmware ADC overshoot -> calibrated band
        reading["gsr"] = round(reading["gsr"] * GSR_FIRMWARE_SCALE, 3)
    reading["accel_mag"] = round(
        (reading["accel_x"] ** 2 + reading["accel_y"] ** 2 + reading["accel_z"] ** 2) ** 0.5, 3)
    reading["gyro_mag"] = round(
        (reading["gyro_x"] ** 2 + reading["gyro_y"] ** 2 + reading["gyro_z"] ** 2) ** 0.5, 3)
    reading["lat"] = d.get("lat") or sim.lat
    reading["lng"] = d.get("lng") or sim.lng
    return reading


async def process_device_payload(d: dict, source: str = "device") -> dict:
    """
    Run one device reading through detection + persistence + broadcast.

    source: 'device' (REST) or 'mqtt' (bridge) — recorded on created alerts.
    Returns {"alerts": n, "reading": reading, "created": [alert, ...]}.
    """
    reading = build_reading(d)
    reading["stress_score"] = stress_score(reading["gsr"], reading["hrv"])

    cal = cal_observe(reading)          # personal baselines adapt online
    with get_db() as db:
        th = one(db.execute("SELECT * FROM thresholds WHERE patient_id=1")) or {}
    patient = {"name": "Margaret Thompson", "age": 78}
    events = evaluate(reading, th, patient, cal)

    sim = get_simulator()
    created = []
    for ev in events:
        alert = sim.create_alert(ev, reading, created_by=source)
        if alert:
            created.append(alert)
    sim.persist(reading)
    sim.persist_device(reading)
    if d.get("lat") is not None and d.get("lng") is not None:
        sim.persist_location(reading)

    # Keep daily activity summary up to date with real device steps
    day = reading["ts"][:10]
    steps = int(reading.get("steps") or 0)
    with get_db() as db:
        db.execute(
            """INSERT INTO activity_daily(date,steps,active_minutes,resting_hr,sleep_hours,calories,distance_km)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(date) DO UPDATE SET
                   steps=MAX(activity_daily.steps, excluded.steps),
                   active_minutes=MAX(activity_daily.active_minutes, excluded.active_minutes),
                   calories=MAX(activity_daily.calories, excluded.calories),
                   distance_km=MAX(activity_daily.distance_km, excluded.distance_km)""",
            (day, steps, max(0, int(steps / 95)), round(reading["heart_rate"] or 0, 1),
             0.0, int(steps * 0.038), round(steps * 0.0007, 2)),
        )
        dev = one(db.execute(
            "SELECT id,name,model,serial,firmware,battery,charging,online,status,mqtt_host,mqtt_port,mqtt_topic,mqtt_tls,protocol,last_seen FROM devices WHERE id=1"
        ))
    reading["device"] = dev

    if sim.on_message:
        await sim.on_message({"type": "telemetry", "data": reading})
        for a in created:
            await sim.on_message({"type": "alert", "data": a})
    return {"alerts": len(created), "reading": reading, "created": created}

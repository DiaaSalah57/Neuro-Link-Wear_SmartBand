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

from .db import get_db, one
from .detection import evaluate, stress_score
from .insights import now_iso
from .simulator import get_simulator


def build_reading(d: dict) -> dict:
    """Normalise an ESP32 / internal payload into the canonical reading shape."""
    sim = get_simulator()
    reading = {
        "ts": now_iso(),
        "heart_rate": d.get("Heart_Rate") or d.get("heart_rate") or 72,
        "temperature": d.get("Body_Temperature") or d.get("temperature") or 36.6,
        "spo2": d.get("Blood_Oxygen") or d.get("spo2") or 97,
        "gsr": d.get("GSR_Value") or d.get("gsr") or 0.4,
        "hrv": d.get("HRV") or d.get("hrv") or 50,
        "steps": int(d.get("Step_Count") or d.get("steps") or 0),
        "activity": d.get("activity") or "Resting",
        "accel_x": float(d.get("Accel_X") or 0.0),
        "accel_y": float(d.get("Accel_Y") or 0.0),
        "accel_z": float(d.get("Accel_Z") or 1.0),
        "gyro_x": float(d.get("Gyro_X") or 0.0),
        "gyro_y": float(d.get("Gyro_Y") or 0.0),
        "gyro_z": float(d.get("Gyro_Z") or 0.0),
        "battery": d.get("battery") or 87,
    }
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

    with get_db() as db:
        th = one(db.execute("SELECT * FROM thresholds WHERE patient_id=1")) or {}
    patient = {"name": "Margaret Thompson", "age": 78}
    events = evaluate(reading, th, patient)

    sim = get_simulator()
    created = []
    for ev in events:
        alert = sim.create_alert(ev, reading, created_by=source)
        if alert:
            created.append(alert)
    sim.persist(reading)

    if sim.on_message:
        await sim.on_message({"type": "telemetry", "data": reading})
        for a in created:
            await sim.on_message({"type": "alert", "data": a})
    return {"alerts": len(created), "reading": reading, "created": created}

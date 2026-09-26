"""
NeuroLink Wear — live telemetry simulator.

Generates a continuous, physiologically plausible stream of wearable readings
(diolurnal rhythm + random walk), plays scripted anomaly scenarios so the
dashboard demonstrates High Stress / Fever / Low Oxygen / Fall Detection in
every session, persists readings to SQLite and pushes everything over the
WebSocket. When real hardware is paired, POST /api/telemetry/ingest (or the
MQTT bridge) feeds the exact same pipeline.
"""
from __future__ import annotations

import asyncio
import math
import random
import time
from datetime import datetime, timezone

from .detection import evaluate, inactivity_event, stress_score, event_alert_payload
from .db import get_db, one, rows
from .insights import generate_explanation

TICK_SECONDS = 2.0
PERSIST_EVERY = 15         # write every 15th tick (30 s) to the DB
LOCATION_EVERY = 10        # location point every 20 s
BROADCAST_STATUS_EVERY = 15

# ── Scripted scenario (seconds within a ~7 minute cycle) ────────────────────
# (name, start_s, end_s)
SCENARIO = [
    ("baseline", 0, 45),
    ("stress", 45, 90),
    ("recover", 90, 135),
    ("walk", 135, 180),
    ("fever", 180, 225),
    ("recover", 225, 270),
    ("desat", 270, 300),
    ("recover", 300, 345),
    ("fall", 345, 362),
    ("post_fall", 362, 420),
]
CYCLE_SECONDS = 420.0

COOLDOWN = 150  # seconds between alerts of the same type


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class WearableSimulator:
    def __init__(self, on_message=None):
        self.on_message = on_message
        self.rng = random.Random()
        self.t0 = time.monotonic()
        self.tick_n = 0
        self.last_alert_at: dict[str, float] = {}
        self.last_movement = time.monotonic()
        self.inactivity_alerted_at = 0.0
        self.override_phase: str | None = None
        self.override_until: float = 0.0

        # Smoothed vitals
        self.hr = 72.0
        self.spo2 = 97.0
        self.temp = 36.6
        self.gsr = 0.42
        self.hrv = 52.0
        self.steps = 2140
        self.battery = 87.0
        self.charging = False
        self.activity = "Resting"
        self._step_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Continue the day's step counter from the database when available
        try:
            midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            with get_db() as db:
                row = one(db.execute(
                    "SELECT MAX(steps) s FROM vitals WHERE ts>=?",
                    (midnight.strftime("%Y-%m-%dT%H:%M:%SZ"),)))
            if row and row["s"] is not None:
                self.steps = int(row["s"])
        except Exception:
            pass

        # GPS around home
        self.lat = 42.3467
        self.lng = -71.1206

    # ── scenario helpers ──────────────────────────────────────────────────
    def _phase(self) -> tuple[str, float]:
        if self.override_phase and time.monotonic() < self.override_until:
            return self.override_phase, 0.3
        t = (time.monotonic() - self.t0) % CYCLE_SECONDS
        for name, s, e in SCENARIO:
            if s <= t < e:
                return name, (t - s) / max(1.0, e - s)
        return "baseline", 0.0

    def force_phase(self, phase: str, seconds: float = 30.0) -> None:
        """Manually drive the simulator into a scenario phase (demo controls).

        Also snaps the smoothed vitals to the scenario targets so the demo
        reacts within one tick (~2 s) instead of drifting for half a minute.
        """
        self.override_phase = phase
        self.override_until = time.monotonic() + seconds
        snapped = {
            "baseline":  dict(hr=74,  spo2=97.4, temp=36.7,  gsr=0.3,  hrv=50, activity="Resting"),
            "stress":    dict(hr=104, spo2=96.2, temp=36.9,  gsr=6.0,  hrv=16, activity="Resting"),
            "fever":     dict(hr=92,  spo2=96.0, temp=38.25, gsr=0.95, hrv=33, activity="Resting"),
            "desat":     dict(hr=70,  spo2=89.3, temp=36.4,  gsr=0.4,  hrv=46, activity="Resting"),
            "fall":      dict(hr=122, spo2=95.4, temp=36.8,  gsr=2.4,  hrv=21, activity="Resting"),
            "post_fall": dict(hr=94,  spo2=96.0, temp=36.8,  gsr=1.6,  hrv=30, activity="Resting"),
            "walk":      dict(hr=96,  spo2=97.0, temp=36.9,  gsr=0.8,  hrv=40, activity="Walking"),
        }.get(phase)
        if snapped:
            for key, val in snapped.items():
                setattr(self, key, val)

    def _smooth(self, current: float, target: float, rate: float = 0.18) -> float:
        return current + (target - current) * rate + self.rng.gauss(0, rate * 1.6)

    # ── one tick ──────────────────────────────────────────────────────────
    def next_reading(self) -> dict:
        phase, prog = self._phase()
        hour = datetime.now(timezone.utc).hour + datetime.now(timezone.utc).minute / 60
        night = hour < 6.5 or hour > 22.5

        # Targets per phase
        if phase == "baseline":
            self.activity = "Sleeping" if night else ("Resting" if self.rng.random() < 0.7 else "Walking")
            t_hr = 62 if night else 74
            t_spo2 = 96.5 if night else 97.4
            t_temp = 36.3 if night else 36.7
            t_gsr, t_hrv = 0.3, 58 if night else 50
        elif phase == "stress":
            self.activity = "Resting"
            t_hr = 104
            t_spo2, t_temp = 96.2, 36.9
            # index ≈ 0.65 — crosses the 0.60 High Stress threshold (4.4µS/18ms scored only 0.58)
            t_gsr, t_hrv = 6.0, 16
        elif phase == "walk":
            self.activity = "Walking"
            t_hr, t_spo2, t_temp = 96, 97.0, 36.9
            t_gsr, t_hrv = 0.8, 40
        elif phase == "fever":
            self.activity = "Resting"
            t_hr = 92
            t_spo2 = 96.0
            t_temp = 38.25
            t_gsr, t_hrv = 0.95, 33
        elif phase == "desat":
            self.activity = "Sleeping" if night else "Resting"
            t_hr = 70
            t_spo2 = 89.3
            t_temp = 36.4
            t_gsr, t_hrv = 0.4, 46
        elif phase == "fall":
            self.activity = "Resting"
            t_hr = 122
            t_spo2, t_temp = 95.4, 36.8
            t_gsr, t_hrv = 2.4, 21
        elif phase == "post_fall":
            self.activity = "Resting"
            t_hr = 94
            t_spo2, t_temp = 96.0, 36.8
            t_gsr, t_hrv = 1.6, 30
        else:  # recover
            self.activity = "Resting"
            t_hr, t_spo2, t_temp = 76, 97.2, 36.7
            t_gsr, t_hrv = 0.5, 52

        self.hr = self._smooth(self.hr, t_hr, 0.16)
        self.spo2 = self._smooth(self.spo2, t_spo2, 0.12)
        self.temp = self._smooth(self.temp, t_temp, 0.05)
        self.gsr = self._smooth(self.gsr, t_gsr, 0.15)
        self.hrv = self._smooth(self.hrv, t_hrv, 0.14)

        # IMU
        if phase == "fall":
            accel = 3.2 + abs(self.rng.gauss(0, 0.35))
            gyro = 3.0 + abs(self.rng.gauss(0, 0.3))
        elif self.activity in ("Walking", "Running", "Exercising"):
            accel = abs(self.rng.gauss(1.1, 0.35))
            gyro = abs(self.rng.gauss(0.9, 0.3))
        else:
            accel = abs(self.rng.gauss(0.12, 0.06))
            gyro = abs(self.rng.gauss(0.08, 0.05))

        if self.activity in ("Walking", "Running", "Exercising"):
            self.steps += 1 if self.rng.random() < 0.6 else 0
            self.last_movement = time.monotonic()

        # Step counter resets at midnight
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._step_day:
            self._step_day = today
            self.steps = 0

        if self.rng.random() < 0.002:
            self.charging = not self.charging
        if not self.charging:
            self.battery = max(5.0, self.battery - 0.004)

        self.gsr = max(0.05, self.gsr)
        self.hrv = max(8.0, self.hrv)

        reading = {
            "ts": _now_iso(),
            "heart_rate": round(self.hr, 1),
            "spo2": round(self.spo2, 1),
            "temperature": round(self.temp, 2),
            "gsr": round(self.gsr, 3),
            "hrv": round(self.hrv, 1),
            "activity": self.activity,
            "accel_x": round(self.rng.gauss(0, accel * 0.7), 3),
            "accel_y": round(self.rng.gauss(0, accel * 0.7), 3),
            "accel_z": round(max(0.1, accel + self.rng.gauss(0, 0.08)), 3),
            "gyro_x": round(self.rng.gauss(0, gyro * 0.6), 3),
            "gyro_y": round(self.rng.gauss(0, gyro * 0.6), 3),
            "gyro_z": round(self.rng.gauss(0, gyro * 0.6), 3),
            "accel_mag": round(accel, 3),
            "gyro_mag": round(gyro, 3),
            "steps": self.steps,
            "battery": int(self.battery),
            "charging": self.charging,
        }
        reading["stress_score"] = stress_score(reading["gsr"], reading["hrv"])

        # GPS slow drift, tighter when resting
        spread = 0.00022 if self.activity in ("Walking", "Running", "Exercising") else 0.00005
        self.lat += self.rng.gauss(0, spread) + (42.3467 - self.lat) * 0.05
        self.lng += self.rng.gauss(0, spread) + (-71.1206 - self.lng) * 0.05
        reading["lat"] = round(self.lat, 6)
        reading["lng"] = round(self.lng, 6)
        return reading

    # ── persistence ──────────────────────────────────────────────────────
    @staticmethod
    def persist(reading: dict) -> None:
        with get_db() as db:
            db.execute(
                """INSERT INTO vitals(ts,heart_rate,spo2,temperature,gsr,hrv,activity,
                                      accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,
                                      accel_mag,gyro_mag,stress_score,steps,battery)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (reading["ts"], reading["heart_rate"], reading["spo2"], reading["temperature"],
                 reading["gsr"], reading["hrv"], reading["activity"], reading["accel_x"],
                 reading["accel_y"], reading["accel_z"], reading["gyro_x"], reading["gyro_y"],
                 reading["gyro_z"], reading["accel_mag"], reading["gyro_mag"],
                 reading["stress_score"], reading["steps"], reading["battery"]),
            )

    @staticmethod
    def persist_location(reading: dict) -> None:
        with get_db() as db:
            db.execute(
                "INSERT INTO location_history(ts,lat,lng,activity,speed) VALUES(?,?,?,?,?)",
                (reading["ts"], reading["lat"], reading["lng"], reading["activity"],
                 1.2 if reading["activity"] == "Walking" else 0.0),
            )

    def persist_device(self, reading: dict) -> None:
        with get_db() as db:
            db.execute(
                "UPDATE devices SET battery=?, charging=?, last_seen=?, online=1 WHERE id=1",
                (reading["battery"], 1 if reading["charging"] else 0, reading["ts"]),
            )

    # ── alerting ─────────────────────────────────────────────────────────
    def _cooldown_ok(self, type_: str) -> bool:
        last = self.last_alert_at.get(type_, 0)
        if time.monotonic() - last < COOLDOWN:
            return False
        self.last_alert_at[type_] = time.monotonic()
        return True

    def create_alert(self, event: dict, reading: dict, created_by: str = "system") -> dict | None:
        patient = {"name": "Margaret Thompson", "age": 78, "conditions": "Hypertension, mild COPD, osteoarthritis"}
        with get_db() as db:
            th = one(db.execute("SELECT * FROM thresholds WHERE patient_id=1")) or {}
        explanation, recommendation, _urgency = generate_explanation(
            event["type"], {**event.get("readings", {}), "time": _now_iso()}, patient
        )
        payload = event_alert_payload(event, patient, reading.get("lat"), reading.get("lng"))
        with get_db() as db:
            cur = db.execute(
                """INSERT INTO alerts(ts,type,severity,status,title,explanation,recommendation,readings,lat,lng,created_by)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (payload["ts"], payload["type"], payload["severity"], payload["status"],
                 payload["title"], explanation, recommendation,
                 __import__("json").dumps(event.get("readings", {})),
                 payload["lat"], payload["lng"], created_by),
            )
            alert_id = cur.lastrowid
            row = one(db.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)))
        return row

    def check_inactivity(self) -> dict | None:
        with get_db() as db:
            th = one(db.execute("SELECT * FROM thresholds WHERE patient_id=1")) or {}
        limit = th.get("inactivity_minutes", 90)
        idle_min = (time.monotonic() - self.last_movement) / 60.0
        if idle_min >= limit and time.monotonic() - self.inactivity_alerted_at > 1800:
            self.inactivity_alerted_at = time.monotonic()
            return inactivity_event(int(idle_min), {"name": "Margaret Thompson"})
        return None

    # ── main loop ────────────────────────────────────────────────────────
    async def run(self) -> None:
        await asyncio.sleep(2.0)
        while True:
            try:
                self.tick_n += 1
                reading = self.next_reading()

                # Evaluate with patient thresholds
                patient = {"name": "Margaret Thompson", "age": 78}
                with get_db() as db:
                    th = one(db.execute("SELECT * FROM thresholds WHERE patient_id=1")) or {}
                events = evaluate(reading, th, patient)

                alerts = []
                for ev in events:
                    if self._cooldown_ok(ev["type"]):
                        alert = self.create_alert(ev, reading)
                        if alert:
                            alerts.append(alert)

                inact = self.check_inactivity()
                if inact and self._cooldown_ok("Inactivity"):
                    alert = self.create_alert(inact, reading)
                    if alert:
                        alerts.append(alert)

                if self.tick_n % PERSIST_EVERY == 0:
                    self.persist(reading)
                if self.tick_n % LOCATION_EVERY == 0:
                    self.persist_location(reading)
                if self.tick_n % BROADCAST_STATUS_EVERY == 0:
                    self.persist_device(reading)

                if self.on_message:
                    await self.on_message({"type": "telemetry", "data": reading})
                    for alert in alerts:
                        await self.on_message({"type": "alert", "data": alert})
            except Exception as e:  # keep the stream alive no matter what
                print(f"[simulator] tick error: {e}")
            await asyncio.sleep(TICK_SECONDS)


# Module-level singleton
_sim: WearableSimulator | None = None


def get_simulator(on_message=None) -> WearableSimulator:
    global _sim
    if _sim is None:
        _sim = WearableSimulator(on_message=on_message)
    elif on_message:
        _sim.on_message = on_message
    return _sim

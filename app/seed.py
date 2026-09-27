"""
NeuroLink Wear — demo seed data.

Pre-populates the database with a realistic elderly patient profile, 7 days of
vitals time-series (24h+ fully populated for the live dashboard), a recent fall
detection event with GPS coordinates and dispatch log, AI health summaries,
emergency contacts, paired device + MQTT config and personalized thresholds.
"""
from __future__ import annotations

import json
import math
import random
from datetime import datetime, timedelta, timezone

from .auth import hash_password
from .db import get_db, one
from .detection import stress_score


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


HOME_LAT, HOME_LNG = 30.028018, 31.201973  # Creativa Innovation Hub - Giza, 26H2+6Q5, Ad Doqi, Dokki
FALL_LAT, FALL_LNG = 30.026438, 31.204363


def seed_all() -> None:
    with get_db() as db:
        if one(db.execute("SELECT id FROM users LIMIT 1")):
            return  # already seeded
        _seed_users(db)
        _seed_patient(db)
        _seed_device(db)
        _seed_contacts(db)
        _seed_thresholds(db)
        _seed_vitals(db)
        _seed_alerts(db)
        _seed_summaries(db)
        _seed_activity(db)
        _seed_locations(db)
    _seed_calibration()


# ── Users ────────────────────────────────────────────────────────────────────
def _seed_users(db) -> None:
    t = iso(now())
    users = [
        ("admin@neurolink.health", "admin123", "Dr. Amara Osei", "admin", "+1 (617) 555-0100"),
        ("caregiver@neurolink.health", "caregiver123", "Emily Carter", "caregiver", "+1 (617) 555-0142"),
        ("james@neurolink.health", "caregiver123", "James Thompson", "caregiver", "+1 (617) 555-0177"),
    ]
    for email, pw, name, role, phone in users:
        db.execute(
            "INSERT INTO users(email,password_hash,name,role,phone,created_at) VALUES(?,?,?,?,?,?)",
            (email, hash_password(pw), name, role, phone, t),
        )


# ── Patient ──────────────────────────────────────────────────────────────────
def _seed_patient(db) -> None:
    db.execute(
        """INSERT INTO patients(name,age,gender,avatar_color,address,room,conditions,
                                medications,emergency_note,lat,lng,home_lat,home_lng,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "Margaret Thompson", 78, "Female", "#2563eb",
            "Creativa Innovation Hub - Giza, 26H2+6Q5, Ad Doqi, Dokki, Giza Governorate 3750010",
            "Suite 214",
            "Hypertension, mild COPD, osteoarthritis",
            "Lisinopril 10mg (morning), Salbutamol inhaler (as needed), Calcium + Vitamin D",
            "Hard of hearing — knock loudly. Fall risk: uses walking frame indoors.",
            HOME_LAT, HOME_LNG, HOME_LAT, HOME_LNG, iso(now()),
        ),
    )


# ── Device ───────────────────────────────────────────────────────────────────
def _seed_device(db) -> None:
    t = iso(now())
    db.execute(
        """INSERT INTO devices(name,model,serial,firmware,battery,charging,status,online,
                               mqtt_host,mqtt_port,mqtt_topic,mqtt_username,mqtt_password,mqtt_tls,
                               protocol,last_seen,patient_id,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "Margaret's NeuroLink Band", "NeuroLink Band NL-200", "NLW-8842-A", "2.4.1",
            87, 0, "paired", 1,
            "831c5bf5139c44d898a9ba6f0b3c526c.s1.eu.hivemq.cloud", 8883,
            "neurolink/wear/NLW-8842-A/telemetry", "Neuro_link", "smartband", 1,
            "mqtt", t, 1, t,
        ),
    )
    db.execute(
        """INSERT INTO devices(name,model,serial,firmware,battery,charging,status,online,
                               mqtt_host,mqtt_port,mqtt_topic,mqtt_username,mqtt_password,mqtt_tls,
                               protocol,last_seen,patient_id,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "Bedside Gateway (backup)", "NeuroLink Hub NH-100", "NLH-2210-C", "1.9.0",
            100, 1, "paired", 0,
            "831c5bf5139c44d898a9ba6f0b3c526c.s1.eu.hivemq.cloud", 8883,
            "neurolink/wear/NLH-2210-C/gateway", "Neuro_link", "smartband", 1,
            "mqtt", iso(now() - timedelta(hours=26)), 1, t,
        ),
    )


# ── Contacts ─────────────────────────────────────────────────────────────────
def _seed_contacts(db) -> None:
    t = iso(now())
    contacts = [
        ("James Thompson", "Son (primary contact)", "+1 (617) 555-0177", "james.thompson@example.com", 1, 1, "Lives 10 min away — can reach the residence quickly."),
        ("Dr. Sarah Mitchell", "Primary care physician", "+1 (617) 555-0119", "s.mitchell@dokkiclinic.example", 2, 1, "Dokki Family Clinic — Mon–Fri 8:00–17:00."),
        ("Emily Carter", "Professional caregiver", "+1 (617) 555-0142", "emily.carter@example.com", 2, 1, "On-site weekdays 09:00–18:00."),
        ("Linda Thompson", "Daughter", "+1 (415) 555-0166", "linda.t@example.com", 3, 1, "Out of state — backup contact, prefers SMS."),
        ("Giza Emergency Services", "Emergency medical services", "911", "", 1, 1, "Call for any fall with head impact or unresponsiveness."),
    ]
    for c in contacts:
        db.execute(
            "INSERT INTO contacts(name,relationship,phone,email,priority,can_dispatch,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (*c, t),
        )


# ── Thresholds ───────────────────────────────────────────────────────────────
def _seed_thresholds(db) -> None:
    db.execute(
        """INSERT INTO thresholds(patient_id,hr_low,hr_high,spo2_low,temp_high,temp_low,gsr_high,
                                  hrv_low,stress_high,fall_enabled,fall_accel,inactivity_minutes,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (1, 52, 112, 92, 37.8, 35.5, 0.75, 20, 0.60, 1, 2.8, 90, iso(now())),
    )


# ── Vitals time-series (7 days @ 10 min) ────────────────────────────────────
def _seed_vitals(db) -> None:
    rnd = random.Random(42)
    start = now().replace(minute=0, second=0, microsecond=0) - timedelta(days=7)
    step = timedelta(minutes=10)

    fall_ts = now().replace(hour=18, minute=42, second=0, microsecond=0) - timedelta(days=1)
    stress_ts = now().replace(hour=14, minute=30, second=0, microsecond=0) - timedelta(days=1)
    desat_ts = now().replace(hour=3, minute=10, second=0, microsecond=0) - timedelta(days=2)
    fever_ts = now().replace(hour=15, minute=0, second=0, microsecond=0) - timedelta(days=5)

    rows = []
    t = start
    steps_cum = 0
    current_day = t.strftime("%Y-%m-%d")
    while t < now():
        day = t.strftime("%Y-%m-%d")
        if day != current_day:
            current_day = day
            steps_cum = 0
        hour = t.hour + t.minute / 60.0
        dow = t.weekday()

        # Diurnal baseline
        if hour < 6.5:  # sleeping
            activity = "Sleeping"
            hr = rnd.gauss(61, 3)
            hrv = rnd.gauss(66, 7)
            gsr = abs(rnd.gauss(0.28, 0.08))
            temp = rnd.gauss(36.25, 0.12)
            spo2 = min(99, rnd.gauss(96.8, 0.9))
            accel = abs(rnd.gauss(0.08, 0.05))
            gyro = abs(rnd.gauss(0.05, 0.04))
        elif hour < 9:  # morning routine
            activity = "Walking" if rnd.random() < 0.5 else "Resting"
            hr = rnd.gauss(82 if activity == "Walking" else 72, 5)
            hrv = rnd.gauss(48, 8)
            gsr = abs(rnd.gauss(0.45, 0.15))
            temp = rnd.gauss(36.55, 0.12)
            spo2 = min(99, rnd.gauss(97.2, 0.8))
            accel = abs(rnd.gauss(0.6, 0.3)) if activity == "Walking" else abs(rnd.gauss(0.15, 0.08))
            gyro = abs(rnd.gauss(0.5, 0.25)) if activity == "Walking" else abs(rnd.gauss(0.1, 0.06))
        elif hour < 12:  # active morning
            activity = "Walking" if rnd.random() < 0.55 else ("Exercising" if rnd.random() < 0.12 else "Resting")
            base = {"Walking": 92, "Exercising": 118, "Resting": 74}[activity]
            hr = rnd.gauss(base, 6)
            hrv = rnd.gauss(44 if activity != "Exercising" else 36, 7)
            gsr = abs(rnd.gauss(0.55, 0.2))
            temp = rnd.gauss(36.7, 0.15)
            spo2 = min(99, rnd.gauss(97.0, 0.9))
            accel = abs(rnd.gauss(0.9, 0.4)) if activity != "Resting" else abs(rnd.gauss(0.2, 0.1))
            gyro = abs(rnd.gauss(0.8, 0.35)) if activity != "Resting" else abs(rnd.gauss(0.12, 0.07))
        elif hour < 14:  # midday
            activity = "Resting" if rnd.random() < 0.6 else "Walking"
            hr = rnd.gauss(78 if activity == "Resting" else 95, 6)
            hrv = rnd.gauss(47, 8)
            gsr = abs(rnd.gauss(0.5, 0.18))
            temp = rnd.gauss(36.85, 0.15)
            spo2 = min(99, rnd.gauss(97.1, 0.8))
            accel = abs(rnd.gauss(0.7, 0.3)) if activity == "Walking" else abs(rnd.gauss(0.18, 0.08))
            gyro = abs(rnd.gauss(0.6, 0.28)) if activity == "Walking" else abs(rnd.gauss(0.11, 0.06))
        elif hour < 17:  # afternoon
            activity = "Walking" if rnd.random() < 0.45 else "Resting"
            hr = rnd.gauss(88 if activity == "Walking" else 76, 6)
            hrv = rnd.gauss(46, 8)
            gsr = abs(rnd.gauss(0.52, 0.2))
            temp = rnd.gauss(36.9, 0.16)
            spo2 = min(99, rnd.gauss(96.9, 0.9))
            accel = abs(rnd.gauss(0.75, 0.35)) if activity == "Walking" else abs(rnd.gauss(0.18, 0.09))
            gyro = abs(rnd.gauss(0.65, 0.3)) if activity == "Walking" else abs(rnd.gauss(0.12, 0.07))
        elif hour < 21.5:  # evening
            activity = "Resting" if rnd.random() < 0.75 else "Walking"
            hr = rnd.gauss(71 if activity == "Resting" else 86, 5)
            hrv = rnd.gauss(52, 8)
            gsr = abs(rnd.gauss(0.4, 0.15))
            temp = rnd.gauss(36.6, 0.13)
            spo2 = min(99, rnd.gauss(97.0, 0.8))
            accel = abs(rnd.gauss(0.5, 0.25)) if activity == "Walking" else abs(rnd.gauss(0.14, 0.07))
            gyro = abs(rnd.gauss(0.45, 0.2)) if activity == "Walking" else abs(rnd.gauss(0.09, 0.05))
        else:  # night wind-down
            activity = "Sleeping" if rnd.random() < 0.7 else "Resting"
            hr = rnd.gauss(64 if activity == "Sleeping" else 70, 3.5)
            hrv = rnd.gauss(60, 7)
            gsr = abs(rnd.gauss(0.3, 0.1))
            temp = rnd.gauss(36.35, 0.12)
            spo2 = min(99, rnd.gauss(96.6, 0.9))
            accel = abs(rnd.gauss(0.08, 0.05))
            gyro = abs(rnd.gauss(0.05, 0.04))

        # Weekends slightly calmer
        if dow >= 5 and activity in ("Walking", "Exercising") and rnd.random() < 0.3:
            activity = "Resting"
            hr -= 8

        # ── scripted historical events ──
        if abs((t - stress_ts).total_seconds()) < 900:  # stress episode yesterday
            gsr = 4.2 + rnd.gauss(0, 0.4)
            hrv = max(12, 19 + rnd.gauss(0, 2.5))
            hr = max(95, hr + 28)
            activity = "Resting"

        if abs((t - desat_ts).total_seconds()) < 1500:  # overnight desaturation
            spo2 = 90.5 + rnd.gauss(0, 0.6)
            hr += 6

        if abs((t - fever_ts).total_seconds()) < 2700:  # fever 5 days ago
            temp = 38.1 + rnd.gauss(0, 0.12)
            hr += 14

        if abs((t - fall_ts).total_seconds()) < 600:  # fall yesterday evening
            if abs((t - fall_ts).total_seconds()) < 300:
                accel = 3.4 + abs(rnd.gauss(0, 0.3))
                gyro = 3.1 + abs(rnd.gauss(0, 0.25))
                hr = 118 + rnd.gauss(0, 5)
                activity = "Resting"
            else:
                hr = 92 + rnd.gauss(0, 6)

        # Daily step accumulation (per 10-minute row)
        if activity in ("Walking", "Running", "Exercising"):
            steps_cum += {"Walking": 110, "Running": 220, "Exercising": 150}[activity]

        stress = stress_score(gsr, hrv)
        rows.append((
            iso(t), round(hr, 1), round(spo2, 1), round(temp, 2), round(gsr, 3),
            round(hrv, 1), activity,
            round(rnd.gauss(0, accel * 0.8), 3), round(rnd.gauss(0, accel * 0.8), 3), round(max(0.2, accel + rnd.gauss(0, 0.1)), 3),
            round(rnd.gauss(0, gyro * 0.7), 3), round(rnd.gauss(0, gyro * 0.7), 3), round(rnd.gauss(0, gyro * 0.7), 3),
            round(accel, 3), round(gyro, 3), stress, int(steps_cum), 87,
        ))
        t += step

    db.executemany(
        """INSERT INTO vitals(ts,heart_rate,spo2,temperature,gsr,hrv,activity,
                              accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,
                              accel_mag,gyro_mag,stress_score,steps,battery)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )


# ── Alerts (recent history incl. yesterday's fall with GPS) ─────────────────
def _seed_alerts(db) -> None:
    n = now()
    fall_ts = n.replace(hour=18, minute=42, second=0, microsecond=0) - timedelta(days=1)
    desat_ts = n.replace(hour=3, minute=12, second=0, microsecond=0) - timedelta(days=2)
    stress_ts = n.replace(hour=14, minute=34, second=0, microsecond=0) - timedelta(days=1)
    fever_ts = n.replace(hour=15, minute=8, second=0, microsecond=0) - timedelta(days=5)
    inact_ts = n.replace(hour=13, minute=20, second=0, microsecond=0) - timedelta(days=6)

    alerts = [
        dict(
            ts=iso(fall_ts), type="Fall Detected", severity="critical", status="resolved",
            title="Fall detected in living room — hard impact 3.4 g",
            explanation=(
                "The band's accelerometer recorded a sharp impact spike of 3.4 g combined with a sudden gyro "
                "rotation of 3.1 rad/s at 18:42 — a motion signature strongly consistent with a fall while "
                "Margaret was walking from the armchair to the kitchen. Heart rate jumped to 118 bpm right "
                "after impact, a typical cardiovascular stress response to a fall."
            ),
            recommendation=(
                "• Call Margaret immediately — if there is no answer within 60 seconds, send someone to the location on the map. "
                "• Do not ask Margaret to get up unassisted; falls in elderly patients are frequently followed by a second fall. "
                "• If there is head impact, confusion, or pain in the hip/wrist, arrange medical evaluation today."
            ),
            readings=json.dumps({"heart_rate": 118, "spo2": 95, "temperature": 36.6, "gsr": 2.1, "hrv": 22, "stress": 0.71, "accel_mag": 3.4, "gyro_mag": 3.1, "activity": "Resting"}),
            lat=FALL_LAT, lng=FALL_LNG,
            resolved_at=iso(fall_ts + timedelta(minutes=22)), acknowledged_by="James Thompson", resolved_by="James Thompson",
            created_by="system",
        ),
        dict(
            ts=iso(desat_ts), type="Low Oxygen", severity="high", status="acknowledged",
            title="Overnight desaturation — SpO2 90%",
            explanation=(
                "The pulse-oximeter channel reports 90%, a 2.0 point drop below the configured minimum of 92%. "
                "For someone with Hypertension, mild COPD, osteoarthritis, this may indicate shallow breathing during "
                "light sleep or a developing chest infection. The episode lasted roughly 25 minutes before recovering."
            ),
            recommendation=(
                "• Encourage slow deep breathing and sit Margaret upright — upright posture opens the diaphragm. "
                "• Re-check SpO2 after 5 minutes of rest; if it stays below 92%, contact the physician. "
                "• Ensure the room is ventilated and check that nothing is obstructing the band's sensor against the skin."
            ),
            readings=json.dumps({"heart_rate": 68, "spo2": 90, "temperature": 36.2, "gsr": 0.31, "hrv": 61, "stress": 0.24}),
            lat=HOME_LAT, lng=HOME_LNG,
            acknowledged_by="Dr. Amara Osei", created_by="system",
        ),
        dict(
            ts=iso(stress_ts), type="High Stress", severity="medium", status="resolved",
            title="High stress episode — index 0.78",
            explanation=(
                "Galvanic skin response rose to 4.20 µS while heart-rate variability fell to 19 ms — the classic "
                "electrodermal signature of acute stress or anxiety. The combined stress index reached 0.78/1.00, "
                "well above Margaret's calm baseline, during the physiotherapy session yesterday afternoon."
            ),
            recommendation=(
                "• Guide Margaret through slow paced breathing (4 seconds in, 6 seconds out) for 2–3 minutes. "
                "• Reduce stimulation: quiet room, seated posture, reassuring conversation. "
                "• If stress index stays above 0.60 for more than 20 minutes, check for pain, caffeine or a distressing trigger."
            ),
            readings=json.dumps({"heart_rate": 104, "spo2": 96, "temperature": 37.0, "gsr": 4.2, "hrv": 19, "stress": 0.78, "activity": "Resting"}),
            lat=HOME_LAT, lng=HOME_LNG,
            resolved_at=iso(stress_ts + timedelta(minutes=40)), acknowledged_by="Emily Carter", resolved_by="Emily Carter",
            created_by="system",
        ),
        dict(
            ts=iso(fever_ts), type="Fever", severity="medium", status="resolved",
            title="Fever — 38.1°C",
            explanation=(
                "Skin temperature climbed to 38.1°C, crossing the 37.8°C fever threshold. A sustained rise like this "
                "often points to infection or inflammation; combined with the elevated resting heart rate of 90 bpm "
                "it was worth confirming with an oral thermometer — the caregiver confirmed 37.9°C orally 30 minutes later."
            ),
            recommendation=(
                "• Confirm with an oral or tympanic thermometer and encourage fluid intake. "
                "• Monitor temperature every 30–60 minutes; if it exceeds 38.5°C or persists over 12 hours, contact the GP. "
                "• Watch for accompanying symptoms: shivering, confusion, reduced urination or a new cough."
            ),
            readings=json.dumps({"heart_rate": 90, "spo2": 96, "temperature": 38.1, "gsr": 0.9, "hrv": 31, "stress": 0.55}),
            lat=HOME_LAT, lng=HOME_LNG,
            resolved_at=iso(fever_ts + timedelta(hours=5)), acknowledged_by="Emily Carter", resolved_by="Dr. Sarah Mitchell",
            created_by="system",
        ),
        dict(
            ts=iso(inact_ts), type="Inactivity", severity="medium", status="resolved",
            title="No movement for 108 minutes",
            explanation=(
                "The motion sensors recorded no meaningful movement for 108 minutes during waking hours. "
                "Prolonged immobility in elderly patients raises the risk of stiffness, pressure sores, blood clots "
                "and unnoticed falls. The caregiver check-in confirmed Margaret was reading in the garden."
            ),
            recommendation=(
                "• Send a quick check-in message or call — confirm Margaret is okay and simply resting. "
                "• If there is no response within 10 minutes, treat as a potential fall or medical event and dispatch help. "
                "• Encourage a short assisted walk; gentle movement reduces stiffness and clot risk."
            ),
            readings=json.dumps({"inactive_minutes": 108}),
            lat=HOME_LAT, lng=HOME_LNG,
            resolved_at=iso(inact_ts + timedelta(minutes=35)), acknowledged_by="Emily Carter", resolved_by="Emily Carter",
            created_by="system",
        ),
    ]

    ids = {}
    for a in alerts:
        cur = db.execute(
            """INSERT INTO alerts(ts,type,severity,status,title,explanation,recommendation,readings,
                                  lat,lng,acknowledged_by,resolved_at,resolved_by,created_by)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (a["ts"], a["type"], a["severity"], a["status"], a["title"], a["explanation"],
             a["recommendation"], a["readings"], a["lat"], a["lng"], a.get("acknowledged_by", ""),
             a.get("resolved_at"), a.get("resolved_by", ""), a.get("created_by", "system")),
        )
        ids[a["type"]] = cur.lastrowid

    # Dispatch log for the fall
    t = iso(fall_ts + timedelta(minutes=1))
    for contact_id, channel, status, msg in [
        (1, "call", "delivered", "EMERGENCY: Fall detected for Margaret Thompson at 18:42. Location: Creativa Innovation Hub - Giza, Ad Doqi, Dokki. Please respond."),
        (3, "sms", "delivered", "NeuroLink Wear alert: Margaret's band detected a fall at 18:42. You are listed as an on-site caregiver. Respond to Suite 214."),
        (2, "sms", "delivered", "FYI: Fall detected for patient Margaret Thompson at 18:42. Family has been contacted. Incident report to follow."),
    ]:
        db.execute(
            "INSERT INTO dispatches(alert_id,contact_id,channel,status,message,sent_by,ts) VALUES(?,?,?,?,?,?,?)",
            (ids["Fall Detected"], contact_id, channel, status, msg, "system", t),
        )
    db.execute(
        "INSERT INTO dispatches(alert_id,contact_id,channel,status,message,sent_by,ts) VALUES(?,?,?,?,?,?,?)",
        (ids["Low Oxygen"], 2, "sms", "delivered", "NeuroLink Wear: overnight desaturation (SpO2 90%) for Margaret Thompson. Review recommended.", "system", iso(desat_ts + timedelta(minutes=4))),
    )


# ── AI summaries ─────────────────────────────────────────────────────────────
def _seed_summaries(db) -> None:
    n = now()
    entries = [
        (
            n - timedelta(hours=3), "daily", "Daily health summary — Margaret",
            "Margaret's overnight readings were stable: resting heart rate averaged 61 bpm with HRV near 66 ms, "
            "and oxygen saturation held at 96–98% after the brief desaturation two nights ago resolved. "
            "She completed an estimated 2,840 steps, mostly a morning walk with the frame and an afternoon "
            "corridor loop. Stress markers stayed low all day (peak index 0.31). Temperature peaked at 36.9°C — "
            "fully normal. No falls were detected today. Overall outlook for tomorrow is positive: keep hydration "
            "and the evening walk routine.",
            json.dumps(["stable-oxygen", "stable-temperature", "calm", "good-mobility"]), 0.92, None,
        ),
        (
            n.replace(hour=19, minute=20, second=0, microsecond=0) - timedelta(days=1), "event", "Fall incident analysis — 18:42",
            "At 18:42 yesterday the band captured a 3.4 g impact with 3.1 rad/s rotational change while Margaret "
            "transitioned from the armchair toward the kitchen — the device's fall model classified this as a "
            "high-confidence fall (ensemble anomaly score 0.81). Heart rate spiked to 118 bpm and recovered within "
            "8 minutes, and SpO2 never dropped below 95%, which are reassuring signs. James Thompson answered the "
            "dispatch call within 40 seconds and was on site within 11 minutes. Margaret reported soreness in the "
            "right hip but no head impact. Recommendation: review walking-frame placement in the kitchen doorway "
            "and schedule a physiotherapy balance assessment this week.",
            json.dumps(["fall-risk", "resolved", "family-notified"]), 0.55, None,
        ),
        (
            n - timedelta(days=1, hours=6), "daily", "Daily health summary — yesterday",
            "Yesterday began calmly, but a clear stress episode peaked at 14:34 (index 0.78) during the "
            "physiotherapy session — GSR rose to 4.2 µS while HRV dropped to 19 ms. Margaret recovered well after "
            "rest and breathing exercises. The evening fall at 18:42 was the day's critical event (see the fall "
            "incident analysis). Overnight oxygen and temperature returned to baseline. Estimated 3,120 steps. "
            "Tomorrow looks stable — protect the evening rest window to keep HRV trending up.",
            json.dumps(["stress-episode", "fall-risk", "recovered"]), 0.61, None,
        ),
        (
            n - timedelta(days=2, hours=5), "daily", "Daily health summary — 2 days ago",
            "A brief overnight desaturation to 90% SpO2 occurred at 03:12 and self-resolved within ~25 minutes — "
            "common in light sleep with mild COPD, but worth mentioning at the next GP visit if it repeats. "
            "Daytime readings were otherwise unremarkable: HR 74 bpm average, temperature 36.7°C peak, calm stress "
            "profile. 2,410 steps recorded. Sleep quality appears improved versus the previous week.",
            json.dumps(["desaturation", "stable-temperature", "sleep-improving"]), 0.74, None,
        ),
        (
            n - timedelta(days=5, hours=4), "daily", "Daily health summary — 5 days ago",
            "A mild fever episode (38.1°C) was recorded mid-afternoon and confirmed orally at 37.9°C by the "
            "caregiver. It resolved within 5 hours with fluids and rest — no further temperature excursions "
            "since. Heart rate was elevated during the episode (90 bpm) and normalized overnight. Mobility and "
            "stress markers were normal. Keep the fluid routine going into next week.",
            json.dumps(["temperature-watch", "resolved", "hydration"]), 0.68, None,
        ),
        (
            n - timedelta(days=3, hours=8), "weekly", "Weekly outlook — week to date",
            "Across the past week Margaret's cardiovascular baseline is trending positively: resting HR down from "
            "68 to 63 bpm and average HRV up from 48 to 52 ms. Mobility is consistent (~2,600 steps/day average). "
            "Two incidents required attention (one fall, one overnight desaturation); both were resolved with "
            "family/caregiver support. Focus areas for next week: fall-proofing the kitchen route, repeating the "
            "balance assessment, and monitoring overnight SpO2 for recurrence.",
            json.dumps(["improving-baseline", "fall-prevention", "sleep-watch"]), 0.8, None,
        ),
    ]
    for ts, period, title, body, tags, score, alert_id in entries:
        db.execute(
            "INSERT INTO ai_summaries(ts,period,title,body,tags,score,alert_id) VALUES(?,?,?,?,?,?,?)",
            (iso(ts), period, title, body, tags, score, alert_id),
        )


# ── Daily activity summaries (14 days) ───────────────────────────────────────
def _seed_activity(db) -> None:
    rnd = random.Random(7)
    n = now()
    for d in range(14, -1, -1):
        date = (n - timedelta(days=d)).strftime("%Y-%m-%d")
        weekend = (n - timedelta(days=d)).weekday() >= 5
        steps = int(rnd.gauss(2450 if weekend else 2980, 420))
        steps = max(800, steps)
        if d == 0:  # today — match the live step counter from the vitals table
            row = db.execute(
                "SELECT MAX(steps) s FROM vitals WHERE ts>=?", (date + "T00:00:00Z",)
            ).fetchone()
            steps = int(row["s"] if row and row["s"] else steps * 0.35)
        active = int(steps / 95 + rnd.gauss(0, 6))
        db.execute(
            "INSERT OR REPLACE INTO activity_daily(date,steps,active_minutes,resting_hr,sleep_hours,calories,distance_km) VALUES(?,?,?,?,?,?,?)",
            (date, steps, max(10, active), round(rnd.gauss(64, 3), 1),
             round(rnd.gauss(7.1, 0.6), 1), int(steps * 0.038 + 320), round(steps * 0.0007, 2)),
        )


# ── Location history ─────────────────────────────────────────────────────────
def _seed_locations(db) -> None:
    rnd = random.Random(11)
    n = now()
    rows = []
    t = n - timedelta(days=2)
    lat, lng = HOME_LAT, HOME_LNG
    while t < n:
        hour = t.hour
        # Gentle drift; a couple of "walks" mid-morning and afternoon
        if 9 < hour < 11 or 15 < hour < 17:
            lat += rnd.gauss(0, 0.00018)
            lng += rnd.gauss(0, 0.00018)
            activity, speed = "Walking", round(abs(rnd.gauss(1.1, 0.3)), 2)
        else:
            lat += (HOME_LAT - lat) * 0.2 + rnd.gauss(0, 0.00004)
            lng += (HOME_LNG - lng) * 0.2 + rnd.gauss(0, 0.00004)
            activity, speed = ("Sleeping" if hour < 6.5 else "Resting"), 0.0
        rows.append((iso(t), round(lat, 6), round(lng, 6), activity, speed))
        t += timedelta(minutes=15)
    # Exact fall location point
    rows.append((iso(n.replace(hour=18, minute=42, second=0, microsecond=0) - timedelta(days=1)), FALL_LAT, FALL_LNG, "Resting", 0.0))
    rows.append((iso(n), round(HOME_LAT, 6), round(HOME_LNG, 6), "Resting", 0.0))
    db.executemany(
        "INSERT INTO location_history(ts,lat,lng,activity,speed) VALUES(?,?,?,?,?)", rows
    )

def _seed_calibration() -> None:
    """Demo calibration: auto-fit from the seeded 24 h + two guided references."""
    try:
        from .calibration import add_reference, auto_fit
        fit = auto_fit(1, hours=24)
        add_reference("oral_temp", 36.9, band_value=36.4,
                      note="Morning oral thermometer reading (seeded demo)")
        add_reference("pulse_ox", 97.0, band_value=96.6,
                      note="Clinical oximeter spot-check (seeded demo)")
        print(f"[seed] calibration auto-fit from {fit['points']} vitals + 2 guided references")
    except Exception as e:
        print(f"[seed] calibration skipped: {e}")

"""
NeuroLink Wear — REST API.

All dashboard data access: auth, telemetry, alerts, AI insights, emergency
dispatch, contacts / devices / thresholds CRUD, trends analytics and admin
user management.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .auth import (
    create_token,
    get_current_user,
    hash_password,
    require_admin,
    require_staff,
    verify_password,
)
from .db import get_db, one, rows
from .insights import build_daily_summary, generate_explanation, now_iso
from .simulator import get_simulator
from . import mqtt as mqtt_mod
from . import calibration as cal_mod
from . import equations as eq_mod
from .ingest import process_device_payload

router = APIRouter(prefix="/api")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ───────────────────────────────────────────────────────────── auth ─────────
class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(body: LoginIn):
    with get_db() as db:
        user = one(db.execute("SELECT * FROM users WHERE email=?", (body.email.lower().strip(),)))
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user)
    return {
        "token": token,
        "user": {k: user[k] for k in ("id", "email", "name", "role", "phone")},
    }


@router.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user


# ─────────────────────────────────────────────────────────── patient ────────
@router.get("/patient")
def get_patient(user: dict = Depends(require_staff)):
    with get_db() as db:
        return one(db.execute("SELECT * FROM patients WHERE id=1"))


class PatientIn(BaseModel):
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    address: str | None = None
    room: str | None = None
    conditions: str | None = None
    medications: str | None = None
    emergency_note: str | None = None
    avatar_color: str | None = None


@router.put("/patient")
def update_patient(body: PatientIn, user: dict = Depends(require_admin)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, "Nothing to update")
    sets = ", ".join(f"{k}=?" for k in data)
    with get_db() as db:
        db.execute(f"UPDATE patients SET {sets}, updated_at=? WHERE id=1", (*data.values(), now_iso()))
        return one(db.execute("SELECT * FROM patients WHERE id=1"))


# ───────────────────────────────────────────────────────── telemetry ────────
@router.get("/telemetry/latest")
def telemetry_latest(user: dict = Depends(require_staff)):
    with get_db() as db:
        v = one(db.execute("SELECT * FROM vitals ORDER BY ts DESC, id DESC LIMIT 1"))
        dev = one(db.execute("SELECT id,name,model,serial,firmware,battery,charging,online,status,mqtt_host,mqtt_port,mqtt_topic,mqtt_username,mqtt_password,mqtt_tls,protocol,last_seen FROM devices WHERE id=1"))
    if dev:
        dev["bridge_status"] = mqtt_mod.bridge_status().get("status", "stopped")
    if not v:
        return {"device": dev, "waiting": True}
    v["device"] = dev
    return v


@router.get("/telemetry/history")
def telemetry_history(
    hours: float = Query(24, ge=1, le=24 * 30),
    max_points: int = Query(360, ge=20, le=2000),
    user: dict = Depends(require_staff),
):
    since = _iso(datetime.now(timezone.utc) - timedelta(hours=hours))
    with get_db() as db:
        data = rows(db.execute(
            """SELECT ts,heart_rate,spo2,temperature,gsr,hrv,activity,stress_score,accel_mag,gyro_mag,steps
               FROM vitals WHERE ts>=? ORDER BY ts ASC""", (since,)))
    if len(data) > max_points:
        stride = len(data) / max_points
        data = [data[int(i * stride)] for i in range(max_points)]
    return {"points": len(data), "data": data}


@router.get("/telemetry/activity")
def telemetry_activity(days: int = Query(14, ge=1, le=60), user: dict = Depends(require_staff)):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_db() as db:
        data = rows(db.execute("SELECT * FROM activity_daily WHERE date>=? ORDER BY date ASC", (since,)))
        today = rows(db.execute(
            """SELECT activity, COUNT(*) as n FROM vitals
               WHERE ts>=? GROUP BY activity""", (_iso(datetime.now(timezone.utc) - timedelta(days=1)),)))
    return {"days": data, "today_activity": today}


class IngestIn(BaseModel):
    Heart_Rate: float | None = None
    heart_rate: float | None = None
    Body_Temperature: float | None = None
    temperature: float | None = None
    Blood_Oxygen: float | None = None
    spo2: float | None = None
    GSR_Value: float | None = None
    gsr: float | None = None
    HRV: float | None = None
    hrv: float | None = None
    Step_Count: float | None = None
    steps: float | None = None
    Accel_X: float = 0.0
    Accel_Y: float = 0.0
    Accel_Z: float = 1.0
    Gyro_X: float = 0.0
    Gyro_Y: float = 0.0
    Gyro_Z: float = 0.0
    activity: str = "Resting"
    Activity_Status: str | None = None
    Sweat_Response: float | None = None
    ts: str | None = None
    lat: float | None = None
    lng: float | None = None


@router.post("/telemetry/ingest")
async def telemetry_ingest(body: IngestIn, request: Request):
    """
    Device / MQTT-bridge ingest. Accepts the ESP32 payload shape
    (Heart_Rate, Body_Temperature, ...) or the internal shape.
    Secured via ?device_key= or a staff bearer token.
    """
    key = request.query_params.get("device_key", "")
    if key != "neurolink-demo-key":
        try:
            get_current_user(request)
        except HTTPException:
            raise HTTPException(401, "device_key or bearer token required")

    result = await process_device_payload(body.model_dump(), source="device")
    return {"ok": True, "alerts": result["alerts"], "reading": result["reading"]}


@router.post("/demo/trigger")
def demo_trigger(kind: str = Query(...), user: dict = Depends(require_staff)):
    """Demo controls: drive the simulator into a scripted scenario."""
    mapping = {"fall": "fall", "stress": "stress", "fever": "fever", "desat": "desat", "normal": "baseline", "walk": "walk"}
    if kind not in mapping:
        raise HTTPException(400, f"kind must be one of {list(mapping)}")
    get_simulator().force_phase(mapping[kind], 28.0)
    return {"ok": True, "phase": mapping[kind]}


# ────────────────────────────────────────────────────────────── alerts ──────
@router.get("/alerts")
def list_alerts(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    type: str | None = Query(None),
    hours: float = Query(24 * 7, ge=1, le=24 * 60),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(require_staff),
):
    since = _iso(datetime.now(timezone.utc) - timedelta(hours=hours))
    q = "SELECT * FROM alerts WHERE ts>=?"
    args: list = [since]
    if status and status != "all":
        q += " AND status=?"
        args.append(status)
    if severity and severity != "all":
        q += " AND severity=?"
        args.append(severity)
    if type and type != "all":
        q += " AND type=?"
        args.append(type)
    q += " ORDER BY ts DESC LIMIT ?"
    args.append(limit)
    with get_db() as db:
        data = rows(db.execute(q, args))
    for a in data:
        try:
            a["readings"] = json.loads(a.get("readings") or "{}")
        except Exception:
            a["readings"] = {}
    return {"count": len(data), "data": data}


@router.get("/alerts/summary")
def alerts_summary(user: dict = Depends(require_staff)):
    today = _iso(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))
    with get_db() as db:
        by_status = rows(db.execute("SELECT status, COUNT(*) n FROM alerts GROUP BY status"))
        by_severity = rows(db.execute("SELECT severity, COUNT(*) n FROM alerts GROUP BY severity"))
        by_type = rows(db.execute("SELECT type, COUNT(*) n FROM alerts GROUP BY type ORDER BY n DESC"))
        today_n = one(db.execute("SELECT COUNT(*) n FROM alerts WHERE ts>=?", (today,)))["n"]
        recent = rows(db.execute("SELECT * FROM alerts ORDER BY ts DESC LIMIT 5"))
    for a in recent:
        try:
            a["readings"] = json.loads(a.get("readings") or "{}")
        except Exception:
            a["readings"] = {}
    return {
        "by_status": {r["status"]: r["n"] for r in by_status},
        "by_severity": {r["severity"]: r["n"] for r in by_severity},
        "by_type": {r["type"]: r["n"] for r in by_type},
        "today": today_n,
        "recent": recent,
    }


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, user: dict = Depends(require_staff)):
    with get_db() as db:
        a = one(db.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)))
        if not a:
            raise HTTPException(404, "Alert not found")
        if a["status"] == "active":
            db.execute(
                "UPDATE alerts SET status='acknowledged', acknowledged_by=? WHERE id=?",
                (user["name"], alert_id),
            )
        return one(db.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)))


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, user: dict = Depends(require_staff)):
    with get_db() as db:
        a = one(db.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)))
        if not a:
            raise HTTPException(404, "Alert not found")
        db.execute(
            "UPDATE alerts SET status='resolved', resolved_at=?, resolved_by=? WHERE id=?",
            (now_iso(), user["name"], alert_id),
        )
        return one(db.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)))


class SosIn(BaseModel):
    note: str = "Emergency SOS button pressed from the dashboard"


@router.post("/alerts/sos")
async def sos(body: SosIn, user: dict = Depends(require_staff)):
    """One-press emergency trigger from the sticky quick-actions bar."""
    sim = get_simulator()
    event = {
        "type": "Emergency SOS",
        "severity": "critical",
        "title": "SOS triggered — immediate assistance requested",
        "readings": {"time": now_iso()},
    }
    alert = sim.create_alert(event, {"lat": sim.lat, "lng": sim.lng}, created_by=user["name"])
    if alert and sim.on_message:
        await sim.on_message({"type": "alert", "data": alert})
    return alert


# ───────────────────────────────────────────────────────── AI summaries ─────
@router.get("/ai/summaries")
def ai_summaries(limit: int = Query(10, ge=1, le=50), user: dict = Depends(require_staff)):
    with get_db() as db:
        data = rows(db.execute("SELECT * FROM ai_summaries ORDER BY ts DESC LIMIT ?", (limit,)))
    for s in data:
        try:
            s["tags"] = json.loads(s.get("tags") or "[]")
        except Exception:
            s["tags"] = []
    return {"count": len(data), "data": data}


@router.post("/ai/summaries/generate")
async def ai_generate(user: dict = Depends(require_staff)):
    """Compose a fresh AI health summary from the latest 24 h of data."""
    with get_db() as db:
        patient = one(db.execute("SELECT * FROM patients WHERE id=1"))
        window = rows(db.execute(
            """SELECT heart_rate,spo2,temperature,gsr,hrv,activity,stress_score FROM vitals
               WHERE ts>=? ORDER BY ts ASC""",
            (_iso(datetime.now(timezone.utc) - timedelta(hours=24)),)))
        alerts = rows(db.execute("SELECT * FROM alerts WHERE ts>=? AND type='Fall Detected'",
                                 (_iso(datetime.now(timezone.utc) - timedelta(hours=24)),)))
    summary = build_daily_summary(patient, window, alerts)
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO ai_summaries(ts,period,title,body,tags,score) VALUES(?,?,?,?,?,?)",
            (now_iso(), "daily", summary["title"], summary["body"],
             json.dumps(summary["tags"]), summary["score"]),
        )
        row = one(db.execute("SELECT * FROM ai_summaries WHERE id=?", (cur.lastrowid,)))
    row["tags"] = summary["tags"]
    return row


# ─────────────────────────────────────────────────────────── dispatch ───────
class DispatchIn(BaseModel):
    alert_id: int | None = None
    contact_ids: list[int] = Field(default_factory=list)
    channel: str = "sms"
    message: str = ""


@router.post("/dispatch")
def dispatch(body: DispatchIn, user: dict = Depends(require_staff)):
    if not body.contact_ids:
        raise HTTPException(400, "Select at least one emergency contact")
    sent = []
    ts = now_iso()
    with get_db() as db:
        for cid in body.contact_ids:
            c = one(db.execute("SELECT * FROM contacts WHERE id=?", (cid,)))
            if not c:
                continue
            msg = body.message or (
                f"NeuroLink Wear emergency dispatch: Margaret Thompson may need immediate assistance. "
                f"Please respond. Live dashboard: NeuroLink Wear Safety view."
            )
            cur = db.execute(
                "INSERT INTO dispatches(alert_id,contact_id,channel,status,message,sent_by,ts) VALUES(?,?,?,?,?,?,?)",
                (body.alert_id, cid, body.channel, "delivered", msg, user["name"], ts),
            )
            sent.append(one(db.execute(
                """SELECT d.*, c.name as contact_name, c.relationship, c.phone FROM dispatches d
                   JOIN contacts c ON c.id=d.contact_id WHERE d.id=?""", (cur.lastrowid,))))
    return {"ok": True, "dispatched": sent}


@router.get("/dispatches")
def list_dispatches(alert_id: int | None = None, limit: int = 50, user: dict = Depends(require_staff)):
    with get_db() as db:
        if alert_id:
            data = rows(db.execute(
                """SELECT d.*, c.name as contact_name, c.relationship, c.phone FROM dispatches d
                   LEFT JOIN contacts c ON c.id=d.contact_id WHERE d.alert_id=? ORDER BY d.ts DESC""",
                (alert_id,)))
        else:
            data = rows(db.execute(
                """SELECT d.*, c.name as contact_name, c.relationship, c.phone FROM dispatches d
                   LEFT JOIN contacts c ON c.id=d.contact_id ORDER BY d.ts DESC LIMIT ?""", (limit,)))
    return {"count": len(data), "data": data}


# ─────────────────────────────────────────────────────────── location ───────
@router.get("/location/latest")
def location_latest(user: dict = Depends(require_staff)):
    with get_db() as db:
        return one(db.execute("SELECT * FROM location_history ORDER BY ts DESC, id DESC LIMIT 1"))


@router.get("/location/history")
def location_history(hours: float = Query(24, ge=1, le=24 * 30), user: dict = Depends(require_staff)):
    since = _iso(datetime.now(timezone.utc) - timedelta(hours=hours))
    with get_db() as db:
        data = rows(db.execute("SELECT * FROM location_history WHERE ts>=? ORDER BY ts ASC", (since,)))
    if len(data) > 400:
        stride = len(data) / 400
        data = [data[int(i * stride)] for i in range(400)]
    return {"count": len(data), "data": data}


# ─────────────────────────────────────────────────────────── contacts ───────
class ContactIn(BaseModel):
    name: str
    relationship: str
    phone: str
    email: str = ""
    priority: int = 2
    can_dispatch: bool = True
    notes: str = ""


@router.get("/contacts")
def list_contacts(user: dict = Depends(require_staff)):
    with get_db() as db:
        return rows(db.execute("SELECT * FROM contacts ORDER BY priority ASC, name ASC"))


@router.post("/contacts")
def create_contact(body: ContactIn, user: dict = Depends(require_staff)):
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO contacts(name,relationship,phone,email,priority,can_dispatch,notes,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (body.name, body.relationship, body.phone, body.email, body.priority,
             1 if body.can_dispatch else 0, body.notes, now_iso()),
        )
        return one(db.execute("SELECT * FROM contacts WHERE id=?", (cur.lastrowid,)))


@router.put("/contacts/{contact_id}")
def update_contact(contact_id: int, body: ContactIn, user: dict = Depends(require_staff)):
    with get_db() as db:
        if not one(db.execute("SELECT id FROM contacts WHERE id=?", (contact_id,))):
            raise HTTPException(404, "Contact not found")
        db.execute(
            """UPDATE contacts SET name=?,relationship=?,phone=?,email=?,priority=?,can_dispatch=?,notes=?
               WHERE id=?""",
            (body.name, body.relationship, body.phone, body.email, body.priority,
             1 if body.can_dispatch else 0, body.notes, contact_id),
        )
        return one(db.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)))


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, user: dict = Depends(require_staff)):
    with get_db() as db:
        if not one(db.execute("SELECT id FROM contacts WHERE id=?", (contact_id,))):
            raise HTTPException(404, "Contact not found")
        db.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    return {"ok": True}


# ─────────────────────────────────────────────────────────── devices ────────
class DeviceIn(BaseModel):
    name: str
    model: str = "NeuroLink Band NL-200"
    serial: str
    firmware: str = "2.4.1"
    status: str = "paired"
    mqtt_host: str = "831c5bf5139c44d898a9ba6f0b3c526c.s1.eu.hivemq.cloud"
    mqtt_port: int = 8883
    mqtt_topic: str = "neurolink/sensors/data"
    mqtt_username: str = "Neuro_link"
    mqtt_password: str = "smartband"
    mqtt_tls: bool = True
    protocol: str = "mqtt"
    patient_id: int | None = 1


@router.get("/devices")
def list_devices(user: dict = Depends(require_staff)):
    with get_db() as db:
        return rows(db.execute("SELECT * FROM devices ORDER BY id ASC"))


@router.post("/devices")
async def create_device(body: DeviceIn, user: dict = Depends(require_admin)):
    with get_db() as db:
        if one(db.execute("SELECT id FROM devices WHERE serial=?", (body.serial,))):
            raise HTTPException(409, "A device with this serial already exists")
        cur = db.execute(
            """INSERT INTO devices(name,model,serial,firmware,status,mqtt_host,mqtt_port,mqtt_topic,
                                   mqtt_username,mqtt_password,mqtt_tls,protocol,patient_id,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (body.name, body.model, body.serial, body.firmware, body.status, body.mqtt_host,
             body.mqtt_port, body.mqtt_topic, body.mqtt_username, body.mqtt_password,
             1 if body.mqtt_tls else 0, body.protocol, body.patient_id, now_iso()),
        )
        dev = one(db.execute("SELECT * FROM devices WHERE id=?", (cur.lastrowid,)))
    if dev and dev.get("mqtt_host"):
        import asyncio
        async def _on_payload(payload, _src="mqtt"):
            await process_device_payload(payload, source=_src)
        mqtt_mod.start_bridge(
            {
                "host": dev["mqtt_host"], "port": dev["mqtt_port"] or 8883,
                "username": dev["mqtt_username"] or "", "password": dev["mqtt_password"] or "",
                "topic": dev["mqtt_topic"] or "neurolink/sensors/data",
                "tls": bool(dev["mqtt_tls"]), "client_id": f"neurolink-bridge-{dev['serial']}",
            },
            _on_payload,
            loop=asyncio.get_running_loop(),
        )
    return dev


@router.put("/devices/{device_id}")
async def update_device(device_id: int, body: DeviceIn, user: dict = Depends(require_admin)):
    with get_db() as db:
        if not one(db.execute("SELECT id FROM devices WHERE id=?", (device_id,))):
            raise HTTPException(404, "Device not found")
        db.execute(
            """UPDATE devices SET name=?,model=?,serial=?,firmware=?,status=?,mqtt_host=?,mqtt_port=?,
                                  mqtt_topic=?,mqtt_username=?,mqtt_password=?,mqtt_tls=?,protocol=?,patient_id=?
               WHERE id=?""",
            (body.name, body.model, body.serial, body.firmware, body.status, body.mqtt_host,
             body.mqtt_port, body.mqtt_topic, body.mqtt_username, body.mqtt_password,
             1 if body.mqtt_tls else 0, body.protocol, body.patient_id, device_id),
        )
        dev = one(db.execute("SELECT * FROM devices WHERE id=?", (device_id,)))
    if dev and dev.get("mqtt_host"):
        import asyncio
        async def _on_payload(payload, _src="mqtt"):
            await process_device_payload(payload, source=_src)
        mqtt_mod.start_bridge(
            {
                "host": dev["mqtt_host"], "port": dev["mqtt_port"] or 8883,
                "username": dev["mqtt_username"] or "", "password": dev["mqtt_password"] or "",
                "topic": dev["mqtt_topic"] or "neurolink/sensors/data",
                "tls": bool(dev["mqtt_tls"]), "client_id": f"neurolink-bridge-{dev['serial']}",
            },
            _on_payload,
            loop=asyncio.get_running_loop(),
        )
    return dev


@router.delete("/devices/{device_id}")
def delete_device(device_id: int, user: dict = Depends(require_admin)):
    with get_db() as db:
        if not one(db.execute("SELECT id FROM devices WHERE id=?", (device_id,))):
            raise HTTPException(404, "Device not found")
        db.execute("DELETE FROM devices WHERE id=?", (device_id,))
    return {"ok": True}


@router.post("/devices/{device_id}/test-connection")
def test_connection(device_id: int, user: dict = Depends(require_staff)):
    """
    Real MQTT broker connection test for the pairing flow.

    Performs an actual DNS → TCP → TLS → MQTT CONNECT/CONNACK handshake with
    the stored broker credentials (e.g. HiveMQ Cloud) and reports the precise
    stage that failed. No simulation.
    """
    with get_db() as db:
        dev = one(db.execute("SELECT * FROM devices WHERE id=?", (device_id,)))
    if not dev:
        raise HTTPException(404, "Device not found")
    res = mqtt_mod.test_broker(
        host=dev["mqtt_host"] or "",
        port=int(dev["mqtt_port"] or 8883),
        username=dev["mqtt_username"] or "",
        password=dev["mqtt_password"] or "",
        topic=dev["mqtt_topic"] or "",
        tls=bool(dev["mqtt_tls"]),
    )
    return {
        "ok": res["ok"],
        "stage": res["stage"],
        "broker": res["broker"],
        "topic": res["topic"],
        "latency_ms": res["latency_ms"],
        "message": res["message"],
        "return_code": res.get("return_code"),
    }


# ────────────────────────────────────────────────────── calibration ────────
class ReferenceIn(BaseModel):
    kind: str
    value: float
    band_value: float | None = None
    note: str = ""


class CalibrationManualIn(BaseModel):
    baselines: dict | None = None
    personal_rules: dict | None = None


@router.get("/calibration")
def get_calibration(user: dict = Depends(require_staff)):
    """Personal calibration state: baselines, sources, confidence, live scores."""
    state = cal_mod.get_calibration(1)
    with get_db() as db:
        latest = one(db.execute("SELECT * FROM vitals ORDER BY ts DESC, id DESC LIMIT 1"))
    live = None
    if latest:
        s_eq = eq_mod.stress_index(latest["gsr"], latest["hrv"], latest["heart_rate"],
                                   state["baselines"], latest.get("activity") or "Resting")
        f_eq = eq_mod.fever_score(latest["temperature"], latest["heart_rate"], state["baselines"],
                                  state.get("temp_prev"))
        live = {
            "stress": s_eq,
            "fever": f_eq,
            "hr": eq_mod.hr_mismatch(latest["heart_rate"], latest.get("activity") or "Resting", 78, state["baselines"]),
            "spo2_calibrated": round((latest["spo2"] or 0) + state["baselines"].get("spo2_offset", 0.0), 1),
        }
    return {
        "state": state,
        "floors": eq_mod.CLINICAL_FLOORS,
        "reference_kinds": cal_mod.REFERENCE_KINDS,
        "references": cal_mod.list_references(1),
        "live": live,
    }


@router.post("/calibration/auto-fit")
def calibration_auto_fit(user: dict = Depends(require_staff)):
    """Snap baselines to robust percentiles of the last 24 h of vitals."""
    return cal_mod.auto_fit(1, hours=24)


@router.post("/calibration/reference")
def calibration_reference(body: ReferenceIn, user: dict = Depends(require_staff)):
    """Apply one guided reference measurement (oral temp, pulse ox, resting HR/HRV)."""
    try:
        return cal_mod.add_reference(body.kind, body.value, body.band_value, body.note, 1)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/calibration")
def calibration_manual(body: CalibrationManualIn, user: dict = Depends(require_staff)):
    """Manual slider updates to baselines / personal rules (floors not editable)."""
    return cal_mod.apply_manual(body.model_dump(exclude_none=True), 1)


# ───────────────────────────────────────────────────────── thresholds ───────
class ThresholdsIn(BaseModel):
    hr_low: float = 52
    hr_high: float = 112
    spo2_low: float = 92
    temp_high: float = 37.8
    temp_low: float = 35.5
    gsr_high: float = 0.75
    hrv_low: float = 20
    stress_high: float = 0.60
    fall_enabled: bool = True
    fall_accel: float = 2.8
    inactivity_minutes: int = 90


@router.get("/thresholds")
def get_thresholds(user: dict = Depends(require_staff)):
    with get_db() as db:
        return one(db.execute("SELECT * FROM thresholds WHERE patient_id=1"))


@router.put("/thresholds")
def update_thresholds(body: ThresholdsIn, user: dict = Depends(require_staff)):
    d = body.model_dump()
    with get_db() as db:
        db.execute(
            """UPDATE thresholds SET hr_low=?,hr_high=?,spo2_low=?,temp_high=?,temp_low=?,gsr_high=?,
                                     hrv_low=?,stress_high=?,fall_enabled=?,fall_accel=?,inactivity_minutes=?,updated_at=?
               WHERE patient_id=1""",
            (d["hr_low"], d["hr_high"], d["spo2_low"], d["temp_high"], d["temp_low"], d["gsr_high"],
             d["hrv_low"], d["stress_high"], 1 if d["fall_enabled"] else 0, d["fall_accel"],
             d["inactivity_minutes"], now_iso()),
        )
        return one(db.execute("SELECT * FROM thresholds WHERE patient_id=1"))


# ──────────────────────────────────────────────────────────── stats ─────────
@router.get("/stats/overview")
def stats_overview(user: dict = Depends(require_staff)):
    now = datetime.now(timezone.utc)
    since24 = _iso(now - timedelta(hours=24))
    since48 = _iso(now - timedelta(hours=48))
    midnight = _iso(now.replace(hour=0, minute=0, second=0, microsecond=0))
    with get_db() as db:
        w24 = one(db.execute(
            """SELECT AVG(heart_rate) hr, AVG(spo2) spo2, AVG(temperature) temp, AVG(gsr) gsr,
                      AVG(hrv) hrv, AVG(stress_score) stress, MAX(stress_score) stress_peak,
                      MIN(spo2) spo2_min, MAX(temperature) temp_max, COUNT(*) n
               FROM vitals WHERE ts>=?""", (since24,)))
        w48 = one(db.execute(
            """SELECT AVG(heart_rate) hr, AVG(hrv) hrv, AVG(stress_score) stress, AVG(temperature) temp
               FROM vitals WHERE ts>=? AND ts<?""", (since48, since24)))
        steps_today = one(db.execute(
            "SELECT MAX(steps) s FROM vitals WHERE ts>=?", (midnight,)))
        active_alerts = one(db.execute("SELECT COUNT(*) n FROM alerts WHERE status='active'"))["n"]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        act = one(db.execute("SELECT * FROM activity_daily WHERE date=?", (today,)))
    delta = None
    if w48 and w48["hr"]:
        delta = {
            "hr": round((w24["hr"] or 0) - (w48["hr"] or 0), 1),
            "hrv": round((w24["hrv"] or 0) - (w48["hrv"] or 0), 1),
            "stress": round(((w24["stress"] or 0) - (w48["stress"] or 0)) * 100) / 100,
            "temp": round((w24["temp"] or 0) - (w48["temp"] or 0), 2),
        }
    return {
        "window_24h": w24,
        "delta_vs_prev": delta,
        "steps_today": (steps_today or {}).get("s") or (act or {}).get("steps") or 0,
        "active_alerts": active_alerts,
        "today_activity": act,
    }


# ─────────────────────────────────────────────────────────── users ──────────
class UserIn(BaseModel):
    email: str
    name: str
    role: str = "caregiver"
    phone: str = ""
    password: str = ""


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    phone: str | None = None
    password: str | None = None


@router.get("/users")
def list_users(user: dict = Depends(require_admin)):
    with get_db() as db:
        return rows(db.execute("SELECT id,email,name,role,phone,created_at FROM users ORDER BY id ASC"))


@router.post("/users")
def create_user(body: UserIn, user: dict = Depends(require_admin)):
    if body.role not in ("admin", "caregiver"):
        raise HTTPException(400, "role must be admin or caregiver")
    if len(body.password or "") < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    with get_db() as db:
        if one(db.execute("SELECT id FROM users WHERE email=?", (body.email.lower().strip(),))):
            raise HTTPException(409, "Email already registered")
        cur = db.execute(
            "INSERT INTO users(email,password_hash,name,role,phone,created_at) VALUES(?,?,?,?,?,?)",
            (body.email.lower().strip(), hash_password(body.password), body.name, body.role, body.phone, now_iso()),
        )
        return one(db.execute("SELECT id,email,name,role,phone,created_at FROM users WHERE id=?", (cur.lastrowid,)))


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, user: dict = Depends(require_admin)):
    with get_db() as db:
        target = one(db.execute("SELECT * FROM users WHERE id=?", (user_id,)))
        if not target:
            raise HTTPException(404, "User not found")
        if body.role and body.role not in ("admin", "caregiver"):
            raise HTTPException(400, "role must be admin or caregiver")
        if body.role == "caregiver" and target["role"] == "admin":
            admins = one(db.execute("SELECT COUNT(*) n FROM users WHERE role='admin'"))["n"]
            if admins <= 1:
                raise HTTPException(400, "Cannot demote the last admin")
        sets, args = [], []
        for field in ("name", "role", "phone"):
            val = getattr(body, field)
            if val is not None:
                sets.append(f"{field}=?")
                args.append(val)
        if body.password:
            if len(body.password) < 6:
                raise HTTPException(400, "Password must be at least 6 characters")
            sets.append("password_hash=?")
            args.append(hash_password(body.password))
        if sets:
            args.append(user_id)
            db.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", args)
        return one(db.execute("SELECT id,email,name,role,phone,created_at FROM users WHERE id=?", (user_id,)))


@router.delete("/users/{user_id}")
def delete_user(user_id: int, user: dict = Depends(require_admin)):
    if user_id == user["id"]:
        raise HTTPException(400, "You cannot delete your own account")
    with get_db() as db:
        target = one(db.execute("SELECT * FROM users WHERE id=?", (user_id,)))
        if not target:
            raise HTTPException(404, "User not found")
        if target["role"] == "admin":
            admins = one(db.execute("SELECT COUNT(*) n FROM users WHERE role='admin'"))["n"]
            if admins <= 1:
                raise HTTPException(400, "Cannot delete the last admin")
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
    return {"ok": True}

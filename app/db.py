"""
NeuroLink Wear — SQLite database layer.

Single-file schema + connection helpers. The database is created and seeded
automatically on first boot (see app/seed.py) so the dashboard feels fully
operational on first load.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("NEUROLINK_DB", ROOT / "data" / "neurolink.db"))

_lock = threading.RLock()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Thread-safe context manager returning a dict-like cursor connection."""
    with _lock:
        conn = connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def one(cur) -> dict | None:
    r = cur.fetchone()
    return dict(r) if r else None


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin','caregiver')),
    phone         TEXT DEFAULT '',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    age           INTEGER NOT NULL,
    gender        TEXT DEFAULT 'Female',
    avatar_color  TEXT DEFAULT '#2563eb',
    address       TEXT DEFAULT '',
    room          TEXT DEFAULT '',
    conditions    TEXT DEFAULT '',
    medications   TEXT DEFAULT '',
    emergency_note TEXT DEFAULT '',
    lat           REAL NOT NULL,
    lng           REAL NOT NULL,
    home_lat      REAL NOT NULL,
    home_lng      REAL NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    model         TEXT DEFAULT 'NeuroLink Band NL-200',
    serial        TEXT NOT NULL UNIQUE,
    firmware      TEXT DEFAULT '2.4.1',
    battery       INTEGER DEFAULT 100,
    charging      INTEGER DEFAULT 0,
    status        TEXT DEFAULT 'paired' CHECK (status IN ('paired','unpaired','archived')),
    online        INTEGER DEFAULT 1,
    mqtt_host     TEXT DEFAULT 'broker.hivemq.com',
    mqtt_port     INTEGER DEFAULT 1883,
    mqtt_topic    TEXT DEFAULT 'neurolink/sensors',
    mqtt_username TEXT DEFAULT '',
    mqtt_password TEXT DEFAULT '',
    mqtt_tls      INTEGER DEFAULT 1,
    protocol      TEXT DEFAULT 'mqtt',
    last_seen     TEXT,
    patient_id    INTEGER,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    relationship TEXT NOT NULL,
    phone        TEXT NOT NULL,
    email        TEXT DEFAULT '',
    priority     INTEGER DEFAULT 1,
    can_dispatch INTEGER DEFAULT 1,
    notes        TEXT DEFAULT '',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thresholds (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id         INTEGER,
    hr_low             REAL DEFAULT 50,
    hr_high            REAL DEFAULT 110,
    spo2_low           REAL DEFAULT 92,
    temp_high          REAL DEFAULT 37.8,
    temp_low           REAL DEFAULT 35.5,
    gsr_high           REAL DEFAULT 0.75,
    hrv_low            REAL DEFAULT 20,
    stress_high        REAL DEFAULT 0.60,
    fall_enabled       INTEGER DEFAULT 1,
    fall_accel         REAL DEFAULT 2.8,
    inactivity_minutes INTEGER DEFAULT 90,
    updated_at         TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS vitals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    heart_rate   REAL NOT NULL,
    spo2         REAL NOT NULL,
    temperature  REAL NOT NULL,
    gsr          REAL NOT NULL,
    hrv          REAL NOT NULL,
    activity     TEXT DEFAULT 'Resting',
    accel_x      REAL DEFAULT 0,
    accel_y      REAL DEFAULT 0,
    accel_z      REAL DEFAULT 1,
    gyro_x       REAL DEFAULT 0,
    gyro_y       REAL DEFAULT 0,
    gyro_z       REAL DEFAULT 0,
    accel_mag    REAL DEFAULT 1,
    gyro_mag     REAL DEFAULT 0,
    stress_score REAL DEFAULT 0,
    steps        INTEGER DEFAULT 0,
    battery      INTEGER DEFAULT 100
);
CREATE INDEX IF NOT EXISTS idx_vitals_ts ON vitals(ts);

CREATE TABLE IF NOT EXISTS alerts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts             TEXT NOT NULL,
    type           TEXT NOT NULL,
    severity       TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','acknowledged','resolved')),
    title          TEXT NOT NULL,
    explanation    TEXT NOT NULL DEFAULT '',
    recommendation TEXT NOT NULL DEFAULT '',
    readings       TEXT DEFAULT '{}',
    lat            REAL,
    lng            REAL,
    acknowledged_by TEXT DEFAULT '',
    resolved_at    TEXT,
    resolved_by    TEXT DEFAULT '',
    created_by     TEXT DEFAULT 'system'
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts);

CREATE TABLE IF NOT EXISTS dispatches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id   INTEGER,
    contact_id INTEGER,
    channel    TEXT NOT NULL DEFAULT 'sms',
    status     TEXT NOT NULL DEFAULT 'sent',
    message    TEXT DEFAULT '',
    sent_by    TEXT DEFAULT '',
    ts         TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ai_summaries (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    period  TEXT NOT NULL DEFAULT 'daily',
    title   TEXT NOT NULL,
    body    TEXT NOT NULL,
    tags    TEXT DEFAULT '[]',
    score   REAL DEFAULT 0,
    alert_id INTEGER,
    FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS activity_daily (
    date           TEXT PRIMARY KEY,
    steps          INTEGER DEFAULT 0,
    active_minutes INTEGER DEFAULT 0,
    resting_hr     REAL DEFAULT 0,
    sleep_hours    REAL DEFAULT 0,
    calories       INTEGER DEFAULT 0,
    distance_km    REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS location_history (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    lat      REAL NOT NULL,
    lng      REAL NOT NULL,
    activity TEXT DEFAULT 'Resting',
    speed    REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_loc_ts ON location_history(ts);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_db() -> None:
    with get_db() as db:
        db.executescript(SCHEMA)

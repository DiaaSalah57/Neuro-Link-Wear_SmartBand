# NeuroLink Wear — Health & Safety Monitoring Dashboard

Real-time IoT health & safety monitoring for elderly individuals, their families and caregivers — integrated with the **NeuroLink Wear** smart band.

![status](https://img.shields.io/badge/status-live-brightgreen) ![python](https://img.shields.io/badge/python-3.11+-blue) ![fastapi](https://img.shields.io/badge/FastAPI-0.141-teal)

## What's inside

| Area | Features |
|---|---|
| **Real-time Telemetry** | Live WebSocket stream + cards for Heart Rate, SpO₂, skin temperature, GSR stress index and IMU motion status (activity state, accelerometer / gyroscope magnitudes, steps) |
| **AI Insights & Alerts** | Anomaly detection for **High Stress, Fever, Low Oxygen, Fall Detection** (plus tachycardia, bradycardia, fatigue, inactivity) with severity badges, plain-language AI explanations and actionable recommendations — powered by transparent **equations + per-patient calibration** (no training dataset): automatic baselines, guided reference measurements and two-tier safety thresholds |
| **Emergency Escalation** | Safety view with incident timeline & timestamps, inactivity alerts, live GPS map (OpenStreetMap) with incident markers, and one-click emergency contact dispatch with delivery log |
| **Historical Trends** | Interactive SVG time-series charts (HRV, temperature & SpO₂, stress vs heart rate) with date-range filters (24 h / 48 h / 7 d / 30 d), 14-day activity summaries and clinical threshold overlays |
| **Caregiver & Device Management** | Full CRUD for emergency contacts, wearable pairing with MQTT broker configuration (+ connection test), personalized health alert thresholds, wearer profile and role-based care-team users |
| **Auth** | Role-based login (**Caregiver** vs **Admin**) with persistent HMAC-signed sessions (30 days) and PBKDF2 password hashing |
| **UX** | Medical-grade responsive layout, sidebar navigation, sticky device-connectivity banner, quick SOS trigger, optimistic updates, skeleton loaders, empty states ("No incidents recorded today"), dark/light mode |
| **Seed Data** | Elderly patient profile, 7 days of vitals time-series (full 24 h populated), a recent fall-detection log with GPS + dispatch history, sample AI health summaries, devices, contacts and thresholds — fully operational on first load |

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py            # http://localhost:8000
```

The SQLite database (`data/neurolink.db`) is created and seeded **automatically on first boot**.

### Demo accounts

| Role | Email | Password |
|---|---|---|
| Caregiver | `caregiver@neurolink.health` | `caregiver123` |
| Admin | `admin@neurolink.health` | `admin123` |

The login screen has one-click chips for both accounts.

### Demo scenario controls

On **Live Overview → Quick Actions** there are buttons to drive the telemetry simulator into a scripted `fall`, `stress spike`, `fever` or `low SpO₂` pattern — watch the alert appear with an AI explanation, severity badge and escalation actions in seconds. The simulator also plays a realistic scenario cycle automatically.

## Architecture

```
ESP32 SmartBand (MQTT)  ─┐
                         ├─→  FastAPI backend (app/)  ─→  SQLite (data/neurolink.db)
Simulator / ingest API  ─┘        │            │
                                  │            ├─ detection.py   rule + ensemble anomaly detection
                                  │            ├─ insights.py    plain-language explanations & summaries
                                  │            ├─ auth.py        sessions + roles
                                  │            └─ seed.py        realistic demo dataset
                                  │
                                  ├─ REST API  /api/*   (auth, telemetry, alerts, contacts, devices,
                                  │                     thresholds, dispatch, stats, users…)
                                  └─ WebSocket /ws      (2 s live telemetry, alerts, device status)
                                           │
                                     SPA dashboard (static/)
                                     vanilla ES modules, zero build step
                                     custom SVG charts · Leaflet map · dark/light themes
```

### Data flow

1. The **simulator** (or real hardware via `POST /api/telemetry/ingest?device_key=…`, or the MQTT bridge in `main.py`) emits readings every 2 s.
2. `detection.py` evaluates each reading against the patient's **personalized thresholds** (editable in Management → Alert Thresholds) **and** a calibrated equation layer — `equations.py` (stress index with tonic/phasic EDA split, core-temperature estimate, hypoxic-burden integral, fall physics, expected-HR model) + `calibration.py` (per-patient baselines learned automatically from the stream, plus guided reference points: oral thermometer, clinical pulse-oximeter, resting HR/HRV). A condition fires when either the clinical tier (fixed safety floors that calibration can never move) or the personal σ-tier (z ≥ threshold vs the wearer's own baseline) triggers — see Management → **Calibration**. No training dataset is involved; the same formulas are firmware-reusable on the ESP32.
3. On detection, `insights.py` produces a plain-language **AI explanation + recommendations** (hosted LLM via `HF_TOKEN` when configured, with a robust local narrative fallback).
4. The alert is persisted, broadcast on `/ws`, and appears instantly in the dashboard with severity badge, actions and GPS.
5. Emergency **dispatch** sends to chosen contacts (SMS/call/app) and is logged per incident.

## Key API endpoints

```
POST /api/auth/login                     GET  /api/telemetry/latest
GET  /api/telemetry/history              GET  /api/telemetry/activity
GET  /api/alerts                         POST /api/alerts/{id}/acknowledge|resolve
POST /api/alerts/sos                     GET  /api/ai/summaries
POST /api/ai/summaries/generate          POST /api/dispatch
GET/POST/PUT/DELETE /api/contacts        GET/POST/PUT/DELETE /api/devices
POST /api/devices/{id}/test-connection   GET/PUT /api/thresholds
GET  /api/stats/overview                 GET/POST/PUT/DELETE /api/users   (admin)
POST /api/telemetry/ingest               POST /api/demo/trigger
WS   /ws?token=…                          (live telemetry + alerts)
```

Interactive OpenAPI docs: `http://localhost:8000/docs`.

## Project layout

```
server.py               # entry point
app/
  main.py               # FastAPI app, WebSocket, static hosting
  api.py                # REST API
  auth.py               # PBKDF2 passwords, HMAC sessions, roles
  db.py                 # SQLite schema
  seed.py               # demo dataset
  detection.py          # anomaly detection engine
  insights.py           # AI narrative engine (LLM-ready)
  simulator.py          # live wearable telemetry simulator
static/                 # SPA dashboard (HTML/CSS/ES modules)
Smart_band/             # ESP32 firmware (MAX30105 + GSR + IMU + OLED)
pipeline.py             # original offline ML pipeline (Isolation Forest + LSTM)
models/                 # trained models (activity classifier, scaler, IF, LSTM AE)
Smartbandproject_dataset_finalll.csv  # training dataset
```

## Using real hardware

The ESP32 firmware (`Smart_band/smart_band.ino`) publishes sensor JSON to MQTT topic `neurolink/sensors`. Configure broker settings from **Management → Devices & MQTT** in the dashboard. Without hardware, the built-in simulator keeps every screen alive with realistic readings. The legacy standalone API (`main.py` + `dashboard.html`) is kept for the original MQTT-only workflow.

## Personalized thresholds

Management → Alert Thresholds controls every alert boundary: HR safe window, SpO₂ floor, fever ceiling/floor, stress-index ceiling, HRV fatigue floor, fall-impact acceleration (with enable switch) and inactivity timeout. Changes apply to the next reading (~2 s).

## License & attribution

Part of the **NeuroLink Wear** project — smart-band health monitoring for elderly care.

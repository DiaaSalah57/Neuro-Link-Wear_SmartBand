# NeuroLink Wear — Full Project Report

**Project:** NeuroLink Wear — SmartBand Health & Safety Monitoring Dashboard
**Branch:** `arena/01a0ddd7-neuro-link-wear-smartband` · **HEAD:** `4dd1c5d`
**Report date:** 2026-09-27 · **Status:** all features delivered, QA green (141/141 + 74/74 + 17/17)

---

## 1. What was built

A full-stack, real-time IoT **health & safety monitoring dashboard** (web + mobile-responsive) for
elderly individuals, their families and caregivers, integrated with the **NeuroLink Wear** smart
band. Medical-grade UI: sidebar navigation, sticky device-connectivity banner, quick SOS triggers,
optimistic updates, skeleton loading, distinct empty states, dark/light mode.

**Tech stack:** Python FastAPI + SQLite + WebSockets + Paho-MQTT (backend), vanilla ES-module
JavaScript + SVG charts + Leaflet map (frontend — no framework, no build step), seeded demo data.

### Requirements → delivery map

| # | Requirement | Delivered |
|---|-------------|-----------|
| 1 | **Real-time telemetry** — live stream + cards (HR/BPM, SpO₂, skin temp, GSR stress, IMU motion) | WS stream (`ws.js`) + vital cards with SVG sparklines + IMU panel (activity state, accel/gyro magnitudes, steps). `simulator.py` plays a realistic scenario cycle; `ingest.py` accepts real device payloads too. |
| 2 | **AI insights & alerts** — High Stress, Fever, Low Oxygen, Fall Detection, severity badges, LLM explanations, recommendations | `detection.py` (8 conditions + 24 h inactivity), severity badges, `insights.py` plain-language explanations + actionable recommendations (hosted LLM via `HF_TOKEN` when configured, robust local narrative fallback). **Later upgraded** to dataset-free *equations + calibration* AI (§4.5). |
| 3 | **Emergency escalation** — safety view, events + timestamps, inactivity alerts, map with GPS, one-click dispatch | Safety timeline ("No incidents recorded today" empty state), inactivity alerts, Leaflet map with live GPS, one-click emergency-contact dispatch with logged dispatch history. |
| 4 | **Historical trends** — interactive time-series (HRV, temp, stress, activity), date filters | SVG time-series charts (HRV, temperature & SpO₂, stress vs HR), 24 h/48 h/7 d/30 d range filters, 14-day activity summaries, clinical threshold overlays. |
| 5 | **Caregiver & device management** — contacts CRUD, wearable pairing (MQTT config), personalized thresholds | Management view: contacts CRUD (priority, dispatch flags), device pairing with MQTT broker config + real connection test (`dns→tcp→tls→mqtt→auth→ok` staging), editable per-patient thresholds, wearer profile, care-team user management (admin). |

**Auth:** role-based (Caregiver / Admin), PBKDF2 password hashing, HMAC-signed 30-day sessions,
persistent login across reloads.

**Seed data:** patient Margaret Thompson (78, hypertension/mild COPD/oste…), 7 days of vitals
(full 24 h populated), recent fall with GPS + dispatch history, sample AI summaries, devices,
contacts, thresholds — fully operational on first load.

---

## 2. Architecture

```
server.py (uvicorn :8000)
└── app/
    ├── main.py         FastAPI app + static mount + WS endpoint
    ├── api.py          REST: auth, telemetry, alerts, summaries, dispatch,
    │                   location, contacts, devices, thresholds, calibration,
    │                   trends, stats, users, demo triggers
    ├── auth.py         PBKDF2 + HMAC sessions (X-Auth-Token / bearer / query)
    ├── db.py           SQLite schema (17 tables) + NEUROLINK_DB override
    ├── ingest.py       build_reading + shared device-payload pipeline
    ├── mqtt.py         HiveMQ Cloud bridge (TLS :8883 / WS :8884/mqtt)
    ├── detection.py    Two-tier anomaly detection (clinical + personal σ)
    ├── equations.py    Physiology equation library (firmware-reusable)
    ├── calibration.py  Per-patient baselines, auto-fit, guided references
    ├── insights.py     LLM explanations + local narrative fallback
    ├── simulator.py    Scripted scenario cycle + demo force_phases
    └── seed.py         Demo seed (users, patient, vitals, alerts, GPS…)
static/                 index.html + css/ + js/ (api, app, ui, charts, ws,
                        store, map, views/{login,overview,alerts,safety,
                        trends,management,settings})
pipeline.py + models/   Legacy offline ML pipeline (kept, superseded by the
                        calibration engine for live detection)
```

**Telemetry pipeline:** device/simulator payload → `build_reading` → `calibration.observe()`
(baselines adapt online) → `detection.evaluate()` (two-tier rules) → `insights.generate_explanation()`
→ alert persisted → WebSocket broadcast → UI (badge + explanation + escalation actions).

---

## 3. Work completed — chronological

| Phase | Work | Commit |
|-------|------|--------|
| 1 | **Core platform** — full backend + frontend + auth + simulator + detection + trends + management + seeds (earlier session chain `95d66a9`…`ae242f5`, preserved on remote `Mobile-app` branch) | consolidated into `f57447e`'s history |
| 2 | **HiveMQ Cloud MQTT integration** — real broker config, TLS/WS endpoints, connection-test staging, live ingest bridge on `neurolink/wear/+/telemetry` | `f57447e` |
| 3 | **QA battery** — 141 checks (51 UI + 1 session + 55 backend + 1 WS + 8 sign-in + 25 e2e); caught & fixed **4 real bugs** (§5) | `QA_REPORT.md` |
| 4 | **Sign-in bug root-cause & fix** — wrong password showed "Session expired" | `5bfd129` |
| 5 | **Calibration-style equation engine** — dataset-free AI (the main work of this chat) | `4dd1c5d` |
| 6 | **Ops** — server restarts, sandbox snapshot recoveries, preview up | — |

---

## 4. This chat — the calibration engine (main deliverable)

### 4.1 Request & discussion

Asked: *how to use equations and calibration instead of a training dataset for the AI models —
let's discuss first*. Proposed architecture: transparent physiology equations + per-patient
calibration (auto-baselines + guided reference measurements + two-tier thresholds), trade-offs vs
dataset ML (accuracy on day one, explainability, no drift bias, firmware-portable), open questions
personalization source, reference points, threshold policy, rollout. User decision: **"okay make it
calibration style."**

### 4.2 `app/equations.py` — the equation library

| Equation | Formula / idea |
|---|---|
| Robust z-score | `z = (x − median) / (1.4826·MAD)` — outlier-resistant personal deviation |
| EDA split | tonic SCL = slow EWMA; phasic SCR = `max(0, GSR − tonic)` (sympathetic arousal signal) |
| Stress index | `S = clamp(0.5 + Σσ-evidence/5)` over z(GSR phasic), z(HRV drop), z(HR rise at rest); every term exposed for explanations |
| Core temperature | `T_core ≈ gain·T_skin + offset` — offset personal, from a guided oral measurement |
| Fever score | triangulation: core level + °C/h slope + HR-temperature coupling |
| Hypoxic burden | `B ← 0.85·B + minutes·max(0, 92 − SpO₂)` — sustained desaturation, not single noise |
| Fall physics | 4-stage signature: free-fall → impact (≥2.8 g) → tumble (≥2.4 rad/s) → stillness |
| Expected HR | `HR_exp = HR_rest_personal + (activity demand × age factor)` — chronotropic check |

### 4.3 `app/calibration.py` — per-patient calibration

- **Auto-calibration (unsupervised):** every stream tick folds into slow EWMA baselines
  (resting HR/HRV, tonic GSR, skin temp, SpO₂) with a **quiet gate** so crisis readings never drag
  baselines; robust MAD tracks personal noise; confidence grows with sample count.
- **Auto-fit:** snapshots baselines to robust percentiles (HR p25, HRV p75, GSR p35/p85, …) of the
  last 24 h of stored vitals, returning a before/after diff the UI previews.
- **Guided reference points:** oral thermometer (+ band skin reading at same moment) → personal
  skin→core offset; clinical pulse oximeter → SpO₂ band offset; measured resting HR/HRV → direct
  baselines. Each is logged in `calibration_refs` and badged in the UI.
- **Manual overrides:** slider/number edits, tagged `manual`.
- **Sources tracked per baseline:** `prior | auto | guided | manual` (visible badges).
- **Status flow:** `warming_up` → `active` with a confidence %.

### 4.4 Two-tier safety thresholds

- **Tier 1 — clinical floors** (`CLINICAL_FLOORS`): SpO₂ < 90 % urgent / < 92 % high, core ≥ 37.8 °C
  fever, fall ≥ 2.8 g, resting HR ≥ 140 / ≤ 38 … **fixed constants calibration can never move** —
  a personal baseline must never make a clinical emergency look safe.
- **Tier 2 — personal σ-rules:** stress z ≥ 2.0σ, HRV drop ≥ 40 % vs personal rest, hypoxic burden
  ≥ 3 %·min … editable in the UI.
- **A condition fires when EITHER tier fires** — personalization can only add sensitivity.

### 4.5 Integration & UI

- `detection.py` evaluates every reading with both tiers as **OR-gates** (legacy rules unchanged —
  zero regression; verified by suite). Calibrated terms land in alert `readings` so explanations can
  cite real numbers ("GSR phasic +2.2σ, RMSSD −1.8σ").
- **API:** `GET /api/calibration` (state + floors + refs + live equation breakdown),
  `POST /api/calibration/auto-fit`, `POST /api/calibration/reference`, `PUT /api/calibration`.
- **UI — Management → "Calibration" tab:** status/confidence chips, baseline cards with source
  badges + manual overrides, auto-fit button with diff toast, guided reference wizard, reference
  history table, live equation panel (z-bars, core-temp derivation, HR vs expected, SpO₂ offset +
  burden), two-tier panel (floors read-only + σ-rule sliders).
- **Firmware path:** `equations.py` is pure stateless math — portable to ESP32 as-is.

### 4.6 Results

- `calib_suite.py` — **74/74 backend checks, idempotent across repeated runs** (equations,
  calibration module, two-tier OR-gates, HTTP API, demo-trigger regression).
- `calib_domtest.cjs` (jsdom) — **17/17 DOM checks**: sign-in regression intact, Calibration tab
  renders all panels, auto-fit interaction, guided oral reference applies + shows in history,
  σ-rule slider saves.
- QA_REPORT.md carries a Build-2 appendix with the full tables.

### 4.7 Bug found & fixed in this chat

- **B2-1 — Demo/quick emergency triggers silently did nothing when pressed twice within 10 min**
  (the 600 s duplicate-suppression cooldown also applied to demo drills). `force_phase()` now
  clears the alert cooldown — drills always show their alert; organic suppression unchanged.

### 4.8 Sign-in bug (start of this chat)

Wrong password displayed **"Session expired — please sign in again"** instead of a credentials
error. Root cause: the generic 401 handler ran session re-validation/clear even for `/auth/login`
401s (which mean *bad credentials*), and stale tokens were attached to login requests.
Fix (`5bfd129`): `/auth/login` 401 surfaces the server detail ("Invalid email or password") and
skips session-clear; no token attach on login; offline → "Cannot reach the dashboard server — it
may be restarting…". Verified: `signin_debug.cjs` (6/6) + `expiry_check.cjs` (real expiry still
logs out correctly).

---

## 5. Bugs found & fixed across the project (all re-verified)

QA battery (4):

1. **Confirm dialogs always cancelled** (`ui.js`) — `closeModal()` resolved `false` before `true`;
   every delete/remove/resolve confirmation silently did nothing. Fixed with a decision flag.
2. **Buttons permanently disabled after save** (`management.js`, `alerts.js`) — `e.currentTarget`
   read after `await` is `null` (real browser semantics); save crashed in `finally`. Fixed by
   capturing the button up front.
3. **View/WS lifecycle race** (`app.js`, `ws.js`) — slow renders outliving navigation re-subscribed
   WS handlers and wrote into dead DOM. Fixed by serialized `navigate()`, null-guarded loaders,
   swallowed async listener rejections; Leaflet timeout 8 s → 3 s.
4. **High Stress demo could never fire** (`simulator.py`) — scripted scenario scored 0.58 < 0.60
   threshold. Recalibrated (GSR 6.0 / HRV 16) and `force_phase` snaps vitals within one tick.

This chat (2): sign-in 401-as-session-expiry (`5bfd129`), demo cooldown swallowing drills (B2-1).

---

## 6. QA & test assets

| Asset | Coverage | Result |
|---|---|---|
| `QA_REPORT.md` | 18 sections, 141 checks (UI, session, backend, WS, sign-in, e2e) | **141/141 PASS** |
| `calib_suite.py` (repo root) | 74 checks: equations, calibration, two-tier detection, HTTP API, demo triggers | **74/74 PASS ×2** (idempotent) |
| `/tmp/domtest/*.cjs` (jsdom harnesses) | sign-in (6), session-expiry (6), calibration DOM (17) | **PASS** (recreatable; `npm i jsdom@24`) |

Reproduce: `.venv/bin/python server.py --port 8000`, then `.venv/bin/python calib_suite.py`.

---

## 7. External integrations

- **HiveMQ Cloud** (user-supplied): host `831c5bf5139c44d898a9ba6f0b3c526c.s1.eu.hivemq.cloud`,
  TLS MQTT `:8883`, WS `:8884/mqtt`, user `Neuro_link`; topics
  `neurolink/wear/NLW-8842-A/telemetry`, `neurolink/wear/NLH-2210-C/gateway`.
  `POST /api/devices/test-connection` returns honest staging (`dns|tcp|tls|mqtt|auth|ok`).
  *Sandbox note:* egress is host-allowlisted — TLS to the broker is cut mid-handshake here
  (`stage='tls'`); the bridge works on any network with normal egress. MQTT logic verified with a
  local mock broker.
- **LLM explanations:** optional `HF_TOKEN` hosted inference; deterministic local narrative
  fallback keeps the app fully functional offline.

---

## 8. Repository state

| Commit | Contents |
|---|---|
| `ea12bcb` | Base upload (original `pipeline.py`, `models/`, README) |
| `f57447e` | Full app + MQTT bridge (44 tracked files) |
| `5bfd129` | Sign-in error UX fix (12 files) |
| `4dd1c5d` | Calibration equation engine (22 files, +1305) |
| `?` | This report |

Remote branch `Mobile-app` holds the earlier detailed phase-1 chain. Test DBs, venv and harness
scratch live outside git (`.gitignore`).

---

## 9. Demo guide

1. Sign in: `caregiver@neurolink.health` / `caregiver123` (or `admin@neurolink.health` / `admin123`).
2. **Overview → Quick Actions:** fall / stress spike / fever / low-SpO₂ demo buttons — alert appears
   within ~2 s with severity badge, AI explanation and escalation actions.
3. **Management → Calibration:** press *Auto-fit from 24 h data*, then run the guided wizard
   (e.g. oral 37.1 °C with band 36.5 °C → personal `+0.6 °C` offset, badged `guided`).
4. **Settings:** MQTT broker config + connection test (stages), simulator controls.
5. **Safety:** fall incident timeline + map + one-click dispatch. **Trends:** range-filtered charts.

---

## 10. Environment notes (sandbox)

- Processes die at turn boundaries; `.venv/`, `data/`, `/tmp` and git refs can be snapshot-reset.
  Recovery is scripted and takes <1 min (rebuild venv, `git fetch && git reset --mixed FETCH_HEAD`,
  restart `server.py`) — the app itself is unaffected.
- No real browser in the sandbox (jsdom only; Playwright downloads blocked) — UI verified via the
  jsdom batteries; open the live preview for the real experience.
- TensorFlow absent → legacy `pipeline.py` cannot execute here (it is superseded anyway).

## 11. Natural next steps (suggested)

1. Port `equations.py` + `calibration.py` to ESP32 firmware (same formulas, C implementation).
2. Persist calibration snapshots over time (weekly baseline drift reports for clinicians).
3. Fall-detection state-machine upgrade (free-fall pre-trigger buffer on the device).
4. Mobile-app branch reunion with this dashboard lineage.

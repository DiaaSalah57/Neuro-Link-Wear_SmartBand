# NeuroLink Wear — ESP32 firmware

Edge firmware for the NeuroLink Wear smart band. It samples the full sensor stack,
extracts the features the AI pipeline was trained on, runs deterministic safety
rules (fall detection, SOS) directly on the wrist, and streams everything to the
backend over **MQTT / TLS (HiveMQ Cloud)**.

```
                    ┌────────────── ESP32 ──────────────┐
 MAX3010x ─┐        │ sensorTask (core 1)                │
 MPU6050  ─┤ I2C    │  PPG → HR · SpO2 · HRV(RMSSD)      │
 MLX90614 ─┤ 400k   │  IMU → steps · variance · falls    │      TLS 8883      ┌──────────────┐
 SSD1306  ─┘        │  GSR → µS · stress score           │ ───────────────►   │ HiveMQ Cloud │ ──► main.py / dashboard
 GSR ──── ADC1      │  OLED UI · button · safety FSM     │  sensors/data      │              │ ◄── alerts/status
 NEO-6M ── UART2    │ netTask (core 0)                   │ ◄───────────────   └──────────────┘
 BOOT btn ─ GPIO0   │  Wi-Fi · NTP · MQTT · GPS · JSON   │  alerts/status
                    └────────────────────────────────────┘
```

## 1. Hardware & wiring

| Device | Bus / pin | Notes |
|---|---|---|
| MAX30102 / MAX30105 | I2C `0x57` — SDA **21**, SCL **22** | HR, SpO2, HRV |
| MPU6050 (or MPU6500/9250 clone) | I2C `0x68` (`0x69` if AD0 high) | steps, tremor, falls |
| MLX90614 | I2C `0x5A` | bus is dropped to 100 kHz only while it is read |
| SSD1306 128×64 OLED | I2C `0x3C` | |
| Grove GSR | analog → **GPIO34** (ADC1) | ADC2 pins do not work while Wi-Fi is on |
| NEO-6M GPS | GPS **TX → GPIO16** (RX2), GPS **RX → GPIO17** (TX2) | 9600 baud. On ESP32-**WROVER** boards 16/17 are used by PSRAM — change `PIN_GPS_*` |
| "I'm OK" / SOS button | on-board **BOOT** button (GPIO0, active-low) | short press = OK / next page, hold 3 s = SOS |
| optional haptic motor / buzzer | `PIN_HAPTIC` (default off) | via a transistor |
| optional battery divider | `PIN_BATTERY_ADC` (default off) | any ADC1 pin |

All sensors run from 3.3 V. Every sensor is auto-detected at boot; a missing one is
reported on the serial monitor, the OLED and in the `sensors` object of every MQTT
message — the band keeps running with whatever is connected.

## 2. Software setup

**Board package:** *esp32 by Espressif Systems* (2.0.x or 3.x) — board **"ESP32 Dev Module"**.

**Libraries** (Arduino IDE → Library Manager):

| Library | Author | Used for |
|---|---|---|
| U8g2 | olikraus | OLED |
| SparkFun MAX3010x Pulse and Proximity Sensor Library | SparkFun | PPG + beat detection |
| PubSubClient (≥ 2.8) | Nick O'Leary | MQTT |
| ArduinoJson (6.x or 7.x) | Benoit Blanchon | payloads |
| TinyGPSPlus | Mikal Hart | NMEA parsing |

(The MPU6050 and MLX90614 drivers are built in — no Adafruit dependencies.)

**Credentials:**

```bash
cp Smart_band/secrets_template.h Smart_band/secrets.h   # then edit secrets.h
```

Fill in `WIFI_SSID`, `WIFI_PASSWORD`, `MQTT_HOST` (…`.s1.eu.hivemq.cloud`), `MQTT_USERNAME`,
`MQTT_PASSWORD`. `secrets.h` is git-ignored. Without it the sketch still compiles with
placeholders so you can test the sensors offline.

Open `Smart_band/smart_band.ino`, upload, and open the serial monitor at **115200 baud**.
Type `?` for the demo console.

## 3. Files

| File | Purpose |
|---|---|
| `smart_band.ino` | setup, the two FreeRTOS tasks, serial demo console |
| `config.h` | every pin, interval, threshold and topic |
| `secrets_template.h` → `secrets.h` | Wi-Fi + HiveMQ credentials |
| `certs.h` | Let's Encrypt *ISRG Root X1* (HiveMQ Cloud's CA) |
| `shared_state.h` | structs shared between the tasks, mutex + event queue |
| `ppg.h` | MAX3010x: FIFO, beats, HR, RMSSD, SpO2, contact |
| `imu.h` | MPU6050: motion features, pedometer, fall detector |
| `gsr.h` | ADC → µS, sweat proxy, stress score |
| `thermo.h` | MLX90614 with PEC check, core-temperature estimate |
| `gps.h` | TinyGPSPlus, fix + UTC time fallback |
| `display.h` | OLED pages and safety screens |
| `safety.h` | button handling + escalation state machine |
| `net.h` | Wi-Fi, NTP, TLS MQTT, telemetry/event JSON, alert parsing |

## 4. MQTT contract

### `neurolink/sensors/data` — band → backend, every `PUBLISH_INTERVAL_MS` (2 s)

The first block uses **exactly the column names of the training data**, so
`pipeline.process_reading(payload)` works unchanged.

```json
{
  "device_id": "nlw-7a3f10", "seq": 412, "ts": 1790512301, "uptime_ms": 824000,
  "Heart_Rate": 72.1, "HRV": 45.3, "Blood_Oxygen": 97.2, "Body_Temperature": 36.8,
  "GSR_Value": 1.234, "Sweat_Response": 0.5, "Step_Count": 12,
  "Accel_X": 0.012, "Accel_Y": -0.034, "Accel_Z": 0.998,
  "Gyro_X": 0.001, "Gyro_Y": 0.0, "Gyro_Z": 0.0,

  "Edge_Activity": "Walking", "Stress_Score": 0.42, "Accel_Var": 0.00012, "Gyro_Var": 0.0,
  "Motion_Freq_Hz": 1.8, "Impact_G_Max": 1.21, "Steps_Total": 3456, "Cadence_SPM": 96,
  "Perfusion_Index": 1.23, "Skin_Temperature": 33.8, "Ambient_Temperature": 26.5, "rssi": -61,
  "flags":   { "ppg_contact": true, "hr_valid": true, "spo2_valid": true, "temp_valid": true, "gsr_contact": true },
  "sensors": { "ppg": true, "imu": true, "gsr": true, "thermo": true, "gps": true },
  "safety":  { "state": "idle" },
  "gps":     { "fix": true, "lat": 30.013056, "lon": 31.208853, "age_s": 2, "sats": 7, "hdop": 1.2 }
}
```

Units: accelerometer in **g**, gyroscope in **rad/s**, GSR in **µS**, `Step_Count` =
steps in the last 60 s (rolling), `Body_Temperature` = skin temperature +
`TEMP_SKIN_TO_CORE_OFFSET_C`. When a value is not available (band not worn, sensor
missing) a resting-normal value is substituted and the corresponding `flags` /
`sensors` entry is `false` — **the backend should skip inference while
`flags.ppg_contact` is false**.

### `neurolink/alerts/status` — backend → band

The band renders whatever the backend publishes here. Minimal contract (all
fields optional; the raw output of `process_reading()` is also accepted — severity
is derived from `ensemble` and the message from `llm_advice`):

```json
{ "source": "backend", "device_id": "nlw-7a3f10",
  "condition": "Low Oxygen", "severity": "critical",
  "message": "SpO2 dropped to 89%. Sit down and breathe slowly.",
  "require_ack": true, "ttl_s": 60 }
```

* `severity` `low | medium | high | critical` — `critical` (or `require_ack: true`)
  opens the on-device **"Are you OK?"** prompt with the 30 s countdown.
* Messages with `"source":"device"` or another `device_id` are ignored; `Normal` is not shown.

### `neurolink/alerts/status` — band → everyone (`"source":"device"`)

| `event` | when | severity |
|---|---|---|
| `PROMPT_STARTED` | fall detected / critical alert shown, countdown running | high |
| `ACKNOWLEDGED` | wearer pressed the button inside the window | info |
| `EMERGENCY` | window expired (`trigger: timeout`) or SOS hold (`trigger: sos_button`) | critical |
| `USER_RESPONDED` | wearer pressed the button after an escalation | info |

```json
{ "source": "device", "device_id": "nlw-7a3f10", "event": "EMERGENCY", "severity": "critical",
  "reason": "FALL", "trigger": "timeout", "confidence": "high",
  "impact_g": 4.7, "orientation_change_deg": 82, "ts": 1790512369, "uptime_ms": 99999,
  "message": "Fall detected and NOT acknowledged within 30 s. Wearer may be unconscious.",
  "vitals": { "heart_rate": 72.1, "spo2": 97.2, "temperature": 36.8, "hrv": 45.3, "stress": 0.42, "hr_valid": true, "ppg_contact": true },
  "gps": { "fix": true, "lat": 30.013056, "lon": 31.208853, "age_s": 2, "sats": 7, "hdop": 1.2 },
  "maps_url": "https://maps.google.com/?q=30.013056,31.208853" }
```

`reason` is `FALL`, `SOS_BUTTON` or `BACKEND:<condition>`. Emergency packets are
queued and retried for 10 minutes if the link is down. The backend is expected to do
the SMS / caregiver dispatch when it receives an `EMERGENCY` event.

### `neurolink/device/status` — retained

`{"device_id":"nlw-7a3f10","online":true,"fw":"1.0.0","ip":"…","rssi":-61,"sensors":{…}}`
on connect; the broker publishes `{"device_id":"…","online":false}` (Last-Will) when the
band drops — gives the caregiver dashboard its "device connected" indicator for free.

## 5. Safety workflow on the band

1. **Trigger** — IMU impact > 3 g (free-fall beforehand raises confidence), *or* a
   backend alert with `severity: critical` / `require_ack`, *or* holding the button 3 s (SOS).
2. **Context verification** — after a 1.5 s settle time the band watches 4 s for
   immobility (accel deviation < 0.25 g, gyro < 0.35 rad/s); the change of the gravity
   vector across the event ("was standing, now lying") sets `confidence`.
3. **Local prompt** — OLED "FALL DETECTED — Are you OK?" with countdown; `PROMPT_STARTED`
   is published immediately so caregivers see a pre-alert.
4. **Escalation** — no button press within `ACK_WINDOW_S` (30 s) → `EMERGENCY` packet with
   vitals, GPS fix and a Google Maps link. The screen shows *HELP REQUESTED* until the
   wearer presses the button (`USER_RESPONDED`); holding the button again re-sends.

## 6. Serial demo console (115200 baud)

| key | action |
|---|---|
| `?` | help |
| `s` | full status dump (sensors, Wi-Fi, MQTT, GPS) |
| `j` | print the last telemetry JSON |
| `f` | simulate a fall → prompt → (timeout) emergency |
| `b` | simulate a button press ("I'm OK" / next OLED page) |
| `S` | simulate an SOS long-press |
| `a` / `A` | inject a backend alert (critical with ack / informational) |
| `p` | publish telemetry now |
| `r` | restart |

## 7. Calibration notes

* **PPG contact** — `PPG_CONTACT_IR_MIN` (50 000) suits a fingertip; on the wrist you may
  need 20 000–30 000 and a snug strap. Keep the SparkFun default LED/ADC settings: the
  beat detector expects that signal amplitude.
* **HRV** — RMSSD over the last 20 beats, intervals measured in 10 ms samples (≈8 ms noise floor).
* **SpO2** — ratio-of-ratios with Maxim's calibration curve: an estimate for trend/anomaly
  detection, not a medical measurement.
* **Temperature** — `TEMP_SKIN_TO_CORE_OFFSET_C` (3.0) converts wrist skin temperature to
  the core range the model expects; calibrate against a thermometer. Raw skin and
  ambient values are published too.
* **GSR** — `GSR_MODE 1` uses the Grove GSR formula (open electrodes = Vcc/2 = no contact);
  `GSR_MODE 2` is a linear map for bare-electrode dividers.
* **Falls** — `FALL_IMPACT_G`, `FALL_IMMOBILE_*`, `FALL_PROMPT_MIN_CONFIDENCE` in `config.h`.
  Start permissive (prompt on every impact + immobility) and tighten with real data.

## 8. Backend integration checklist

* `main.py` currently subscribes to `neurolink/sensors` — change it to
  `neurolink/sensors/data` (or `neurolink/sensors/#`) and connect paho-mqtt to the
  HiveMQ host with `tls_set()` + `username_pw_set()`.
* Publish classifications to `neurolink/alerts/status` (contract above) and subscribe to
  the same topic for `"source":"device"` events to trigger caregiver dispatch.
* Skip inference while `flags.ppg_contact` is `false`; log `Impact_G_Max`, `Accel_Var`,
  `Motion_Freq_Hz` for tremor/fatigue trends.

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `MQTT connect failed rc=-2` right after boot | TLS needs a valid clock; the band waits for NTP (≤ 20 s) or a GPS time fix. Check the network allows UDP 123. |
| `rc=-2` persists | wrong host / port 8883 / CA. Try `MQTT_TLS_INSECURE 1` once to isolate a certificate problem. |
| `rc=5` | bad HiveMQ username/password (Access Management → credentials). |
| `MAX3010x not found` | SDA/SCL swapped, 5 V module without level shifting, or address conflict — see the `[i2c] devices:` line. |
| MLX90614 reads fail | some modules dislike 400 kHz on a shared bus; the driver already drops to 100 kHz for its reads — check pull-ups (4.7 kΩ). |
| No GPS sentences | TX/RX crossed; on WROVER boards move away from GPIO16/17. First fix needs sky view (cold start up to ~1 min). |
| Board won't flash | release the BOOT button — it doubles as the "I'm OK" button. |

## 10. Verification

The firmware was compiled on a PC against the real headers of U8g2, the SparkFun
MAX3010x library, PubSubClient, TinyGPSPlus and ArduinoJson 6 **and** 7 (with a mocked
ESP32 core), and the signal-processing / safety logic was exercised with synthetic PPG,
IMU and MQTT data (HR/SpO2/RMSSD accuracy, fall vs. walking, step counts, JSON
contract, prompt → ack / timeout → emergency, SOS). Final validation on the real
hardware is still required — see the serial console commands above.

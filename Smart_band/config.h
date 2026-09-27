/**
 * NeuroLink Wear — firmware configuration
 * ----------------------------------------
 * Every tunable lives here (pins, timing, thresholds, MQTT topics).
 * Wi-Fi / broker credentials live in secrets.h (see secrets_template.h).
 */
#pragma once

// ═══════════════════════════════════════════════════════════════════════════
//  Identity
// ═══════════════════════════════════════════════════════════════════════════
#define FIRMWARE_VERSION          "1.0.0"
#define DEVICE_ID_PREFIX          "nlw-"     // + last 3 MAC bytes → "nlw-7a3f10" (unless DEVICE_ID_OVERRIDE is set)

// ═══════════════════════════════════════════════════════════════════════════
//  Feature switches (1 = compiled in). A sensor that is enabled but not
//  detected on the bus is simply reported as missing — the band keeps running.
// ═══════════════════════════════════════════════════════════════════════════
#define ENABLE_PPG                1   // MAX30102 / MAX30105 → HR, SpO2, HRV (RMSSD)
#define ENABLE_IMU                1   // MPU6050             → motion, steps, fall detection
#define ENABLE_GSR                1   // Grove GSR           → skin conductance / stress
#define ENABLE_THERMO             1   // MLX90614            → skin temperature
#define ENABLE_GPS                1   // NEO-6M              → location for escalation
#define ENABLE_OLED               1   // SSD1306 128x64 I2C
#define ENABLE_SERIAL_CONSOLE     1   // demo / debug commands over USB serial (type '?')

// ═══════════════════════════════════════════════════════════════════════════
//  Pins
// ═══════════════════════════════════════════════════════════════════════════
#define PIN_I2C_SDA               21
#define PIN_I2C_SCL               22
#define PIN_GSR_ADC               34   // ADC1 (ADC2 pins are unusable while Wi-Fi is on)
#define PIN_GPS_RX                16   // ESP32 RX2  ←  GPS TX
#define PIN_GPS_TX                17   // ESP32 TX2  →  GPS RX
#define PIN_BUTTON                0    // on-board BOOT button, active LOW ("I'm OK" / SOS)
#define PIN_HAPTIC                -1   // vibration motor or buzzer (+transistor); -1 = none
#define PIN_BATTERY_ADC           -1   // optional LiPo divider on an ADC1 pin; -1 = none
#define BATTERY_DIVIDER_RATIO     2.0f // (R1+R2)/R2 of the divider

// ═══════════════════════════════════════════════════════════════════════════
//  I2C
// ═══════════════════════════════════════════════════════════════════════════
#define I2C_CLOCK_HZ              400000
#define MLX_I2C_CLOCK_HZ          100000 // MLX90614 is SMBus: max 100 kHz, bus is slowed only during its read
#define I2C_ADDR_MAX3010X         0x57
#define I2C_ADDR_MPU6050          0x68   // 0x69 is tried automatically if AD0 is high
#define I2C_ADDR_MLX90614         0x5A
#define I2C_ADDR_OLED             0x3C

// ═══════════════════════════════════════════════════════════════════════════
//  Timing
// ═══════════════════════════════════════════════════════════════════════════
#define PUBLISH_INTERVAL_MS       2000   // telemetry cadence (spec: 1–5 s)
#define IMU_SAMPLE_MS             20     // 50 Hz
#define GSR_SAMPLE_MS             100
#define THERMO_SAMPLE_MS          1000
#define DISPLAY_FRAME_MS          250
#define SNAPSHOT_MS               100    // how often the sensor task publishes its shared snapshot
#define BOOT_SCREEN_MS            2500

// ═══════════════════════════════════════════════════════════════════════════
//  PPG (MAX3010x)
//  The SparkFun beat detector is tuned for the default sensor setup below;
//  raising LED power / ADC range changes the AC amplitude it expects.
// ═══════════════════════════════════════════════════════════════════════════
#define PPG_LED_BRIGHTNESS        0x1F    // 0x02–0xFF  (0x1F ≈ 6.4 mA)
#define PPG_SAMPLE_AVERAGE        4
#define PPG_SAMPLE_RATE           400     // ÷ average → 100 samples/s into the FIFO
#define PPG_PULSE_WIDTH           411
#define PPG_ADC_RANGE             4096
#define PPG_CONTACT_IR_MIN        50000UL // finger ≈ >50k. On the wrist you may need 20k–30k.
#define HR_MIN_BPM                30
#define HR_MAX_BPM                220
#define HRV_WINDOW_BEATS          20      // RMSSD window (≈15–20 s at rest)
#define PPG_HR_TIMEOUT_MS         5000    // no beat for this long → HR marked invalid
#define PPG_STALE_MS              60000   // no valid HR for this long → stop repeating last value
#define SPO2_MIN_PERFUSION        0.001f  // AC/DC ratio below this = no usable pulse

// ═══════════════════════════════════════════════════════════════════════════
//  IMU (MPU6050) — steps & fall detection
//  Units published: accelerometer in g, gyroscope in rad/s (this matches the
//  training dataset: |a| ≈ 1.0 g while sleeping).
// ═══════════════════════════════════════════════════════════════════════════
#define STEP_WINDOW_MS            60000   // "Step_Count" = steps in the last 60 s (rolling)
#define STEP_MIN_INTERVAL_MS      250     // max cadence 4 steps/s
#define STEP_BOUT_GAP_MS          2000    // gap larger than this ends a walking bout
#define STEP_PEAK_THRESHOLD_G     0.12f   // dynamic-acceleration peak needed for a step
#define STEP_BOUT_MIN_STEPS       3       // rhythmic steps required before counting starts
#define FALL_IMPACT_G             3.0f    // |a| above this = impact candidate
#define FALL_FREEFALL_G           0.45f   // |a| below this shortly before impact = free-fall
#define FALL_SETTLE_MS            1500    // ignore the chaos right after impact
#define FALL_IMMOBILE_WINDOW_MS   4000    // then watch for this long
#define FALL_IMMOBILE_ACCEL_G     0.25f   // |a|-1g deviation counted as "movement"
#define FALL_IMMOBILE_GYRO_RADS   0.35f   // gyro magnitude counted as "movement"
#define FALL_IMMOBILE_MAX_RATIO   0.10f   // ≤10 % "moving" samples in the window = immobile
#define FALL_ORIENT_CHANGE_DEG    45.0f   // orientation change that raises confidence
#define FALL_RETRIGGER_HOLDOFF_MS 30000   // suppress new fall alerts for this long after one is handled
#define FALL_PROMPT_MIN_CONFIDENCE 0      // 0 = prompt on every fall, 1 = medium+ only, 2 = high only
#define MOTION_VAR_WINDOW_MS      2000    // window for Accel_Var / Gyro_Var / Motion_Freq_Hz

// ═══════════════════════════════════════════════════════════════════════════
//  GSR
//  GSR_MODE 1 = Grove GSR v1.x module (op-amp board, formula from Seeed wiki)
//  GSR_MODE 2 = plain voltage divider: map mV linearly onto 0.1–20 µS
// ═══════════════════════════════════════════════════════════════════════════
#define GSR_MODE                  1
#define GSR_SUPPLY_MV             3300
#define GSR_LINEAR_MIN_MV         200     // mode 2 only
#define GSR_LINEAR_MAX_MV         3000    // mode 2 only
#define GSR_MIN_US                0.05f
#define GSR_MAX_US                25.0f
// Normalisation constants copied from models/pipeline_stats.json so the
// on-device stress score matches the backend's Stress_Score.
#define STATS_GSR_MIN             0.1002f
#define STATS_GSR_MAX             19.934f
#define STATS_HRV_MIN             13.604f
#define STATS_HRV_MAX             89.956f
#define STRESS_MED_THRESHOLD      0.45f
#define STRESS_HIGH_THRESHOLD     0.60f   // backend's "Stress" rule fires at 0.60

// ═══════════════════════════════════════════════════════════════════════════
//  Skin temperature (MLX90614)
//  The model was trained on core-range temperatures (36–38 °C) while the
//  sensor reads wrist skin (~32–35 °C). Calibrate this offset against a
//  clinical thermometer; both raw skin and the estimate are published.
// ═══════════════════════════════════════════════════════════════════════════
#define TEMP_SKIN_TO_CORE_OFFSET_C 3.0f
#define TEMP_SKIN_VALID_MIN_C     25.0f   // outside this range the band is probably not worn
#define TEMP_SKIN_VALID_MAX_C     45.0f

// ═══════════════════════════════════════════════════════════════════════════
//  Safety / escalation
// ═══════════════════════════════════════════════════════════════════════════
#define ACK_WINDOW_S              30      // seconds the user has to press "I'm OK"
#define SOS_LONG_PRESS_MS         3000    // hold the button this long = manual SOS
#define BUTTON_DEBOUNCE_MS        40
#define RESOLVED_SCREEN_MS        3000
#define ALERT_DISPLAY_S           20      // default on-screen time for backend alerts
#define SOS_REPEAT_MIN_MS         30000   // min gap between repeated SOS packets
#define HAPTIC_PULSE_MS           300

// ═══════════════════════════════════════════════════════════════════════════
//  Connectivity / MQTT
// ═══════════════════════════════════════════════════════════════════════════
#define MQTT_TOPIC_SENSORS        "neurolink/sensors/data"    // band → backend (telemetry)
#define MQTT_TOPIC_ALERTS         "neurolink/alerts/status"   // backend → band/app, and band → all (emergencies)
#define MQTT_TOPIC_DEVICE_STATUS  "neurolink/device/status"   // retained online/offline (Last-Will)
#define MQTT_USE_TLS              1       // HiveMQ Cloud requires TLS on 8883
#define MQTT_TLS_INSECURE         0       // 1 = skip certificate validation (testing only!)
#define MQTT_KEEPALIVE_S          30
#define MQTT_SOCKET_TIMEOUT_S     10
#define MQTT_BUFFER_BYTES         1536    // PubSubClient default (256) is too small for our JSON
#define MQTT_RECONNECT_MIN_MS     2000
#define MQTT_RECONNECT_MAX_MS     30000
#define NTP_SERVER_1              "pool.ntp.org"
#define NTP_SERVER_2              "time.google.com"
#define TIMEZONE_POSIX            "EET-2EEST,M4.5.5/0,M10.5.4/24"   // Egypt (OLED clock only; MQTT timestamps are UTC epoch)
#define NTP_WAIT_BEFORE_TLS_MS    20000   // TLS needs a valid clock; give NTP this long before trying anyway
#define WIFI_RETRY_MS             15000
#define CONNECTIVITY_WATCHDOG_MIN 15      // reboot if offline this long (0 = disabled; never while an alert is active)
#define PUBLISH_NEUTRAL_WHEN_MISSING 1    // substitute resting-normal values for missing sensors (validity flags still say false)
#define EVENT_OUTBOX_SIZE         4
#define EVENT_OUTBOX_TTL_MS       600000  // keep unsent emergency packets for 10 min

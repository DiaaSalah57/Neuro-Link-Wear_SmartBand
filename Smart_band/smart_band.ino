/**
 * ╔══════════════════════════════════════════════════════════════════════════╗
 * ║  NeuroLink Wear — ESP32 edge firmware                                    ║
 * ║  AI-powered wearable: vitals → edge features → MQTT (HiveMQ Cloud, TLS)  ║
 * ╚══════════════════════════════════════════════════════════════════════════╝
 *
 *  Sensors    MAX30102/30105 (HR · SpO2 · HRV) · MPU6050 (steps · falls · tremor)
 *             Grove GSR (stress) · MLX90614 (skin temp) · NEO-6M GPS · SSD1306 OLED
 *
 *  Tasks      sensorTask  core 1  every I2C device, OLED, button, safety FSM
 *             netTask     core 0  Wi-Fi, NTP, TLS MQTT, GPS UART, JSON
 *             loop()      core 1  serial demo console (type '?')
 *
 *  MQTT       neurolink/sensors/data   ← telemetry JSON every 2 s
 *             neurolink/alerts/status  → backend alerts (OLED) / ← device emergencies
 *             neurolink/device/status  ← retained online/offline (Last-Will)
 *
 *  Wiring     I2C SDA 21 / SCL 22 (all I2C devices + OLED) · GSR → GPIO34
 *             GPS TX → GPIO16 (RX2), GPS RX → GPIO17 (TX2) · BOOT button = "I'm OK" / SOS
 *
 *  Setup      1. copy secrets_template.h → secrets.h and fill in Wi-Fi + HiveMQ
 *             2. install the libraries listed in README.md
 *             3. Board: "ESP32 Dev Module", 115200 baud serial monitor
 *
 *  Modules    config.h · shared_state.h · ppg.h · imu.h · gsr.h · thermo.h ·
 *             gps.h · display.h · safety.h · net.h · certs.h
 */

#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "shared_state.h"
#include "ppg.h"
#include "imu.h"
#include "gsr.h"
#include "thermo.h"
#include "gps.h"
#include "display.h"
#include "safety.h"
#include "net.h"

// ─── Module instances ────────────────────────────────────────────────────────
static PpgSensor     ppg;
static ImuSensor     imu;
static GsrSensor     gsr;
static ThermoSensor  thermo;
static GpsModule     gpsModule;
static Display       display;
static SafetyManager safety;
static NetLink       net;

static bool     g_oledPresent = false;
static uint32_t g_bootMs = 0;

// ─── Helpers ─────────────────────────────────────────────────────────────────
static bool i2cPing(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

static void i2cScan() {
  Serial.print("[i2c] devices:");
  uint8_t found = 0;
  for (uint8_t a = 0x08; a < 0x78; a++) if (i2cPing(a)) { Serial.printf(" 0x%02X", a); found++; }
  Serial.println(found ? "" : " none");
}

static void makeDeviceId() {
#ifdef DEVICE_ID_OVERRIDE
  strcopy(g_deviceId, sizeof g_deviceId, DEVICE_ID_OVERRIDE);
#else
  const uint64_t mac = ESP.getEfuseMac();
  snprintf(g_deviceId, sizeof g_deviceId, "%s%02x%02x%02x", DEVICE_ID_PREFIX,
           (unsigned)((mac >> 24) & 0xFF), (unsigned)((mac >> 32) & 0xFF), (unsigned)((mac >> 40) & 0xFF));
#endif
}

static float readBattery() {
#if PIN_BATTERY_ADC >= 0
  uint32_t mv = 0;
  for (uint8_t i = 0; i < 4; i++) mv += analogReadMilliVolts(PIN_BATTERY_ADC);
  return (mv / 4.0f) * BATTERY_DIVIDER_RATIO / 1000.0f;
#else
  return 0.0f;
#endif
}

// The OLED frame is sent in 8 chunks; the PPG FIFO is drained in between.
static void servicePpgBetweenPages() { ppg.service(millis()); }

// ─── sensorTask (core 1) ─────────────────────────────────────────────────────
static void sensorTask(void*) {
  uint32_t tImu = 0, tSnap = 0, tDisp = 0, tLog = 0;
  Telemetry  t;      memset(&t, 0, sizeof t); t.edgeActivity = "Unknown";
  LinkStatus link;   memset(&link, 0, sizeof link);
  AlertState alert;  memset(&alert, 0, sizeof alert);

  for (;;) {
    const uint32_t now = millis();

    ppg.service(now);                                          // as often as possible
    if (now - tImu >= IMU_SAMPLE_MS) { tImu = now; imu.service(now); }
    gsr.service(now);                                          // self-throttled
    thermo.service(now);                                       // self-throttled

    safety.service(now, imu, alert);

    if (now - tSnap >= SNAPSHOT_MS) {                          // compose + share the snapshot
      tSnap = now;
      t.batteryV = readBattery();
      ppg.fill(t, now);
      imu.fill(t, now);                                        // needs HR → after ppg.fill
      gsr.fill(t);                                             // needs HR/HRV → after ppg.fill
      thermo.fill(t, now);
      safety.fill(t);
      publishTelemetrySnapshot(t);
    }

    if (now - tDisp >= DISPLAY_FRAME_MS && now - g_bootMs >= BOOT_SCREEN_MS) {
      tDisp = now;
      link  = snapshotLink();
      alert = snapshotAlert();
      if (safety.takePageCycle()) display.nextPage();
      display.render(t, link, alert, now, ppg.beatFlash(now), servicePpgBetweenPages);
    }

    if (now - tLog >= 5000) {                                  // heartbeat line on the serial monitor
      tLog = now;
      Serial.printf("[live] HR %.0f%s SpO2 %.0f%s HRV %.0f  T %.1f/%.1f  GSR %.2fuS  steps %u  %s  |a| %.2f  safety=%s\n",
                    t.heartRate, t.hrValid ? "" : "?", t.spo2, t.spo2Valid ? "" : "?", t.hrv,
                    t.skinTempC, t.bodyTempC, t.gsrUs, (unsigned)t.stepsWindow, t.edgeActivity,
                    t.accelMag, safetyStateName(t.safety));
    }

    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

// ─── netTask (core 0) ────────────────────────────────────────────────────────
static void netTask(void*) {
  for (;;) {
    net.service(millis());
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

// ─── setup ───────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.printf("\n[boot] NeuroLink Wear firmware %s\n", FIRMWARE_VERSION);

  stateInit();
  makeDeviceId();
  Serial.printf("[boot] device id: %s\n", g_deviceId);

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.setClock(I2C_CLOCK_HZ);
  i2cScan();

#if ENABLE_OLED
  g_oledPresent = i2cPing(I2C_ADDR_OLED);
#endif
  display.begin(g_oledPresent);
  display.showBoot("initialising sensors", "");

  bool ppgOk = false, imuOk = false, thermoOk = false;
#if ENABLE_PPG
  ppgOk = ppg.begin(Wire);
#endif
#if ENABLE_IMU
  imuOk = imu.begin(Wire);
#endif
#if ENABLE_THERMO
  thermoOk = thermo.begin(Wire);
#endif
#if ENABLE_GSR
  gsr.begin();
#endif
#if ENABLE_GPS
  gpsModule.begin();
#endif
  safety.begin();

  Serial.printf("[boot] PPG %s | IMU %s | THERMO %s | GSR %s | GPS %s | OLED %s\n",
                ppgOk ? "ok" : "--", imuOk ? "ok" : "--", thermoOk ? "ok" : "--",
                ENABLE_GSR ? "ok" : "off", ENABLE_GPS ? "uart" : "off", g_oledPresent ? "ok" : "--");
  if (imuOk) Serial.printf("[boot] IMU WHO_AM_I = 0x%02X\n", imu.whoAmI());
  if (!ppgOk)    Serial.println("[boot] ! MAX3010x not found — check SDA/SCL wiring and 3.3 V");
  if (!imuOk)    Serial.println("[boot] ! MPU6050 not found — fall detection and steps disabled");
  if (!thermoOk) Serial.println("[boot] ! MLX90614 not found — temperature disabled");

  char l1[24], l2[24];
  snprintf(l1, sizeof l1, "PPG %s  IMU %s", ppgOk ? "ok" : "--", imuOk ? "ok" : "--");
  snprintf(l2, sizeof l2, "TMP %s  GPS %s", thermoOk ? "ok" : "--", ENABLE_GPS ? "..": "--");
  display.showBoot(l1, l2);

  net.begin(&gpsModule);
  g_bootMs = millis();

  xTaskCreatePinnedToCore(sensorTask, "sensor", 8192,  nullptr, 3, nullptr, 1);
  xTaskCreatePinnedToCore(netTask,    "net",    16384, nullptr, 1, nullptr, 0);
  Serial.println("[boot] tasks running — type '?' for the demo console");
}

// ─── Serial demo console (loop, core 1) ──────────────────────────────────────
#if ENABLE_SERIAL_CONSOLE
static void printStatus() {
  const Telemetry t = snapshotTelemetry();
  const LinkStatus l = snapshotLink();
  Serial.println("──────── status ────────");
  Serial.printf("id %s  fw %s  up %lus  heap %u\n", g_deviceId, FIRMWARE_VERSION, (unsigned long)(millis() / 1000), (unsigned)ESP.getFreeHeap());
  Serial.printf("PPG  present=%d contact=%d hr=%.1f(%d) spo2=%.1f(%d) hrv=%.1f PI=%.2f%% ir=%lu\n",
                t.ppgPresent, t.ppgContact, t.heartRate, t.hrValid, t.spo2, t.spo2Valid, t.hrv, t.perfusionPct, (unsigned long)t.ir);
  Serial.printf("IMU  present=%d a=(%.2f %.2f %.2f)g |a|=%.2f g=(%.2f %.2f %.2f)rad/s var=%.4f f=%.1fHz steps=%u/%lu %s\n",
                t.imuPresent, t.ax, t.ay, t.az, t.accelMag, t.gx, t.gy, t.gz, t.accelVar, t.motionFreqHz,
                (unsigned)t.stepsWindow, (unsigned long)t.stepsTotal, t.edgeActivity);
  Serial.printf("GSR  %.0fmV raw=%u %.2fuS contact=%d stress=%.2f sweat=%.2f\n", t.gsrMv, t.gsrRaw, t.gsrUs, t.gsrContact, t.stressScore, t.sweat);
  Serial.printf("TEMP present=%d skin=%.2f amb=%.2f body~%.2f valid=%d\n", t.thermoPresent, t.skinTempC, t.ambientTempC, t.bodyTempC, t.tempValid);
  Serial.printf("SAFE state=%s reason=%s\n", safetyStateName(t.safety), t.safetyReason);
  Serial.printf("WIFI up=%d ip=%s rssi=%d | MQTT up=%d rc=%d seq=%lu fails=%lu | time=%s\n",
                l.wifiConnected, l.ip, l.rssi, l.mqttConnected, l.mqttState, (unsigned long)l.seq, (unsigned long)l.publishFailures,
                l.timeSynced ? l.timeSource : "unsynced");
  Serial.printf("GPS  present=%d fix=%d lat=%.6f lon=%.6f sats=%u hdop=%.1f\n", l.gpsPresent, l.gpsFix, l.lat, l.lon, (unsigned)l.sats, l.hdop);
}

static void handleConsole(char c) {
  switch (c) {
    case '?': case 'h':
      Serial.println("──────── NeuroLink Wear console ────────");
      Serial.println(" s  status            j  last telemetry JSON");
      Serial.println(" f  simulate FALL     b  press button (I'm OK / next page)");
      Serial.println(" S  simulate SOS      a  inject backend alert (needs ack)");
      Serial.println(" A  inject info alert p  publish telemetry now");
      Serial.println(" r  restart");
      break;
    case 's': printStatus(); break;
    case 'j': Serial.println(net.lastPayload()); break;
    case 'f': safety.simulateFall();        Serial.println("[demo] fall injected"); break;
    case 'b': safety.simulateButtonPress(); Serial.println("[demo] button press"); break;
    case 'S': safety.simulateSos();         Serial.println("[demo] SOS long-press"); break;
    case 'a': net.injectTestAlert(true);    break;
    case 'A': net.injectTestAlert(false);   break;
    case 'p': net.requestPublish();         Serial.println("[demo] publish requested"); break;
    case 'r': Serial.println("[demo] restarting"); delay(100); ESP.restart(); break;
    default: break;
  }
}
#endif

void loop() {
#if ENABLE_SERIAL_CONSOLE
  while (Serial.available()) handleConsole((char)Serial.read());
#endif
  vTaskDelay(pdMS_TO_TICKS(50));
}

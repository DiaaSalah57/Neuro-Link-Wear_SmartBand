/**
 * NeuroLink Wear — state shared between the two FreeRTOS tasks
 * -------------------------------------------------------------
 *   sensorTask (core 1)  owns every I2C device, the OLED, the button and the
 *                        safety state machine. It publishes a Telemetry
 *                        snapshot ~10×/s.
 *   netTask    (core 0)  owns Wi-Fi, TLS/MQTT, NTP and the GPS UART. It
 *                        publishes a LinkStatus snapshot and incoming alerts.
 *
 * Rules: shared structs are only touched inside stateLock()/stateUnlock()
 * (copy in, copy out — never hold the lock while doing I/O). One-shot device
 * events (fall, SOS, acknowledgements) travel sensorTask → netTask through a
 * FreeRTOS queue.
 */
#pragma once

#include <Arduino.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"
#include "config.h"

// ─── Safety state machine (see safety.h) ────────────────────────────────────
enum SafetyState : uint8_t {
  SAFETY_IDLE = 0,
  SAFETY_PROMPT,      // "Are you OK?" countdown running
  SAFETY_ESCALATED,   // emergency packet sent, waiting for the user to respond
  SAFETY_RESOLVED     // short confirmation screen before returning to idle
};

static inline const char* safetyStateName(SafetyState s) {
  switch (s) {
    case SAFETY_PROMPT:    return "prompt";
    case SAFETY_ESCALATED: return "escalated";
    case SAFETY_RESOLVED:  return "resolved";
    default:               return "idle";
  }
}

// ─── Device-originated events (sensorTask → netTask → MQTT) ─────────────────
enum EventType : uint8_t {
  EVT_PROMPT_STARTED = 0, // local "Are you OK?" prompt shown (pre-alert for caregivers)
  EVT_ACKNOWLEDGED,       // user pressed "I'm OK" inside the window
  EVT_EMERGENCY,          // window expired, or SOS long-press → escalation packet
  EVT_USER_RESPONDED      // user pressed the button after an escalation
};

struct DeviceEvent {
  EventType type;
  char      reason[32];     // cause: "FALL", "SOS_BUTTON", "BACKEND:Low Oxygen", ...
  char      trigger[16];    // what fired it: "detector" | "timeout" | "button" | "sos_button"
  char      confidence[8];  // "high" | "medium" | "low" | ""
  float     impactG;        // peak |a| of the impact (0 if n/a)
  float     orientDeg;      // orientation change across the fall (0 if n/a)
  uint16_t  ackWindowS;
  uint32_t  uptimeMs;
};

// ─── Sensor snapshot (written by sensorTask) ────────────────────────────────
struct Telemetry {
  // PPG
  bool     ppgPresent, ppgContact, hrValid, spo2Valid;
  float    heartRate, hrv, spo2, perfusionPct;
  uint32_t ir, red;
  // IMU  (accel in g, gyro in rad/s)
  bool     imuPresent;
  float    ax, ay, az, gx, gy, gz;
  float    accelMag, accelVar, gyroVar, motionFreqHz, impactGMax;
  uint32_t stepsTotal;
  uint16_t stepsWindow;
  float    cadenceSpm;
  const char* edgeActivity;   // points at a string literal → safe to copy
  // GSR
  bool     gsrPresent, gsrContact;
  uint16_t gsrRaw;
  float    gsrMv, gsrUs, sweat, stressScore;
  // Thermo
  bool     thermoPresent, tempValid;
  float    skinTempC, ambientTempC, bodyTempC;
  // Battery
  float    batteryV;          // 0 when no divider is configured
  // Safety
  SafetyState safety;
  char     safetyReason[32];
  uint32_t promptDeadlineMs;
};

// ─── Connectivity / GPS snapshot (written by netTask) ───────────────────────
struct LinkStatus {
  bool     wifiConnected;
  int8_t   rssi;
  char     ip[16];
  bool     mqttConnected;
  int      mqttState;         // PubSubClient::state()
  uint32_t lastPublishMs;
  uint32_t seq;
  uint32_t publishFailures;
  bool     timeSynced;
  char     timeSource[5];     // "ntp" | "gps" | ""
  bool     gpsPresent, gpsFix;
  double   lat, lon;
  float    altM, speedKmh, hdop;
  uint8_t  sats;
  uint32_t gpsAgeMs;
};

// ─── Last alert received from the backend on MQTT_TOPIC_ALERTS ──────────────
struct AlertState {
  uint32_t id;                // increments per alert, 0 = none yet
  uint32_t receivedMs;
  uint32_t ttlMs;
  bool     requireAck;        // backend asked for a local "Are you OK?" prompt
  char     severity[10];      // low | medium | high | critical | info
  char     condition[24];     // e.g. "Low Oxygen"
  char     ensemble[28];      // e.g. "High Confidence Anomaly"
  char     message[72];       // short human-readable text (OLED shows ≤ 2 lines)
};

// ─── Globals ────────────────────────────────────────────────────────────────
static Telemetry         g_telemetry;
static LinkStatus        g_link;
static AlertState        g_alert;
static SemaphoreHandle_t g_stateMutex = nullptr;
static QueueHandle_t     g_eventQueue = nullptr;
static char              g_deviceId[24] = "nlw-000000";

static inline void stateInit() {
  memset(&g_telemetry, 0, sizeof(g_telemetry));
  memset(&g_link,      0, sizeof(g_link));
  memset(&g_alert,     0, sizeof(g_alert));
  g_telemetry.edgeActivity = "Unknown";
  g_stateMutex = xSemaphoreCreateMutex();
  g_eventQueue = xQueueCreate(8, sizeof(DeviceEvent));
}

static inline bool stateLock(uint32_t timeoutMs = 50) {
  return xSemaphoreTake(g_stateMutex, pdMS_TO_TICKS(timeoutMs)) == pdTRUE;
}
static inline void stateUnlock() { xSemaphoreGive(g_stateMutex); }

// Copy helpers — short critical sections, no I/O inside.
static inline void publishTelemetrySnapshot(const Telemetry& t) {
  if (stateLock()) { g_telemetry = t; stateUnlock(); }
}
static inline Telemetry snapshotTelemetry() {
  Telemetry t = g_telemetry;                 // fallback if the lock times out
  if (stateLock()) { t = g_telemetry; stateUnlock(); }
  return t;
}
static inline void publishLinkSnapshot(const LinkStatus& l) {
  if (stateLock()) { g_link = l; stateUnlock(); }
}
static inline LinkStatus snapshotLink() {
  LinkStatus l = g_link;
  if (stateLock()) { l = g_link; stateUnlock(); }
  return l;
}
static inline void publishAlert(const AlertState& a) {
  if (stateLock()) { g_alert = a; stateUnlock(); }
}
static inline AlertState snapshotAlert() {
  AlertState a = g_alert;
  if (stateLock()) { a = g_alert; stateUnlock(); }
  return a;
}

static inline bool postEvent(const DeviceEvent& e) {
  return g_eventQueue && xQueueSend(g_eventQueue, &e, 0) == pdTRUE;
}
static inline bool takeEvent(DeviceEvent& e) {
  return g_eventQueue && xQueueReceive(g_eventQueue, &e, 0) == pdTRUE;
}

// Safe bounded string copy (always NUL-terminated).
static inline void strcopy(char* dst, size_t dstSize, const char* src) {
  if (!dst || dstSize == 0) return;
  if (!src) { dst[0] = '\0'; return; }
  strncpy(dst, src, dstSize - 1);
  dst[dstSize - 1] = '\0';
}

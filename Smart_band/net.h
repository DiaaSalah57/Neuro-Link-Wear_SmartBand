/**
 * NeuroLink Wear — connectivity (Wi-Fi · NTP · TLS MQTT to HiveMQ Cloud)
 * -----------------------------------------------------------------------
 *  Runs on core 0 (netTask). Fully non-blocking state machine:
 *    Wi-Fi STA (auto-reconnect) → NTP / GPS clock → TLS handshake →
 *    MQTT session with Last-Will → subscribe alerts → publish telemetry.
 *
 *  Topics
 *    MQTT_TOPIC_SENSORS        band → cloud   telemetry JSON every PUBLISH_INTERVAL_MS
 *    MQTT_TOPIC_ALERTS         cloud → band   AI classifications / prompts (parsed here)
 *                              band → cloud   device events: PROMPT_STARTED, ACKNOWLEDGED,
 *                                             EMERGENCY, USER_RESPONDED  ("source":"device")
 *    MQTT_TOPIC_DEVICE_STATUS  retained {"online":true|false} via Last-Will
 *
 *  Emergency packets are kept in a small outbox and retried until the broker
 *  accepts them, so a Wi-Fi hiccup during a fall does not lose the alert.
 */
#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <sys/time.h>
#include <math.h>
#include "config.h"
#include "shared_state.h"
#include "certs.h"
#include "gps.h"

#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #include "secrets_template.h"
  #warning "Smart_band/secrets.h not found - using placeholder credentials from secrets_template.h"
#endif

#if ARDUINOJSON_VERSION_MAJOR >= 7
  typedef JsonDocument NlwJsonDoc;
  #define NLW_NESTED(doc, key) ((doc)[key].to<JsonObject>())
#else
  typedef StaticJsonDocument<MQTT_BUFFER_BYTES> NlwJsonDoc;
  #define NLW_NESTED(doc, key) ((doc).createNestedObject(key))
#endif

class NetLink {
public:
  void begin(GpsModule* gps) {
    _gps = gps;
    s_instance = this;

    WiFi.persistent(false);
    WiFi.mode(WIFI_STA);
    WiFi.setHostname(g_deviceId);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    _wifiAttemptMs = millis();

#if MQTT_USE_TLS
  #if MQTT_TLS_INSECURE
    _secure.setInsecure();
  #else
    _secure.setCACert(HIVEMQ_ROOT_CA);
  #endif
    _secure.setHandshakeTimeout(15);
    _mqtt.setClient(_secure);
#else
    _mqtt.setClient(_plain);
#endif
    _mqtt.setServer(MQTT_HOST, MQTT_PORT);
    _mqtt.setCallback(NetLink::mqttTrampoline);
    _mqtt.setBufferSize(MQTT_BUFFER_BYTES);
    _mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
    _mqtt.setSocketTimeout(MQTT_SOCKET_TIMEOUT_S);
    Serial.printf("[net] broker %s:%d  tls=%d  id=%s\n", MQTT_HOST, (int)MQTT_PORT, (int)MQTT_USE_TLS, g_deviceId);
    _placeholderCreds = strcmp(WIFI_SSID, "YOUR_WIFI_SSID") == 0 || strstr(MQTT_HOST, "xxxxxxxx") != nullptr;
    if (_placeholderCreds)
      Serial.println("[net] !!! Credentials are still the template placeholders — copy secrets_template.h to secrets.h and fill it in");
  }

  /** Call continuously from netTask. */
  void service(uint32_t nowMs) {
    serviceWifi(nowMs);
    serviceClock(nowMs);
    if (_gps) _gps->service();
    serviceMqtt(nowMs);
    drainEvents(nowMs);
    serviceOutbox(nowMs);
    if (_mqtt.connected() && (_publishNow || nowMs - _lastPublishMs >= PUBLISH_INTERVAL_MS)) {
      _publishNow = false;
      publishTelemetry(nowMs);
    }
    if (nowMs - _lastLinkSnapMs >= 500) { _lastLinkSnapMs = nowMs; updateLinkSnapshot(nowMs); }
    watchdog(nowMs);
  }

  void requestPublish()             { _publishNow = true; }
  bool mqttConnected()              { return _mqtt.connected(); }
  const char* lastPayload() const   { return _txBuf; }
  time_t epochNow() const           { time_t n = time(nullptr); return n > 1700000000 ? n : 0; }

  /** Inject a fake backend alert (serial console 'a') — exercises the prompt path without the cloud. */
  void injectTestAlert(bool requireAck) {
    const char* json = requireAck
      ? "{\"source\":\"backend\",\"condition\":\"Low Oxygen\",\"severity\":\"critical\",\"require_ack\":true,\"message\":\"SpO2 dropped to 89%. Sit down and breathe slowly.\"}"
      : "{\"source\":\"backend\",\"condition\":\"Stress\",\"severity\":\"medium\",\"ensemble\":\"Low Confidence Anomaly\",\"message\":\"HRV falling while GSR rises. Take a short break.\"}";
    onMessage(MQTT_TOPIC_ALERTS, (const uint8_t*)json, strlen(json));
  }

private:
  static NetLink* s_instance;

  GpsModule* _gps = nullptr;
#if MQTT_USE_TLS
  WiFiClientSecure _secure;
#else
  WiFiClient _plain;
#endif
  PubSubClient _mqtt;

  bool     _wifiUp = false, _mqttUp = false, _everOnline = false, _publishNow = false, _placeholderCreds = false;
  bool     _ntpStarted = false, _timeSynced = false;
  char     _timeSource[5] = "";
  uint32_t _wifiAttemptMs = 0, _wifiUpSinceMs = 0, _lastOnlineMs = 0;
  uint32_t _nextMqttAttemptMs = 0, _backoffMs = MQTT_RECONNECT_MIN_MS;
  uint32_t _lastPublishMs = 0, _lastLinkSnapMs = 0, _seq = 0, _publishFailures = 0, _alertCounter = 0;
  char     _txBuf[MQTT_BUFFER_BYTES];

  struct PendingEvent { bool used; uint32_t createdMs; DeviceEvent ev; Telemetry snap; };
  PendingEvent _outbox[EVENT_OUTBOX_SIZE] = {};

  // ── Wi-Fi ────────────────────────────────────────────────────────────────
  void serviceWifi(uint32_t nowMs) {
    const bool up = WiFi.status() == WL_CONNECTED;
    if (up != _wifiUp) {
      _wifiUp = up;
      if (up) {
        _wifiUpSinceMs = nowMs;
        char ip[16]; ipToStr(WiFi.localIP(), ip, sizeof ip);
        Serial.printf("[net] Wi-Fi connected  ip=%s  rssi=%d\n", ip, (int)WiFi.RSSI());
      } else {
        Serial.println("[net] Wi-Fi lost");
      }
    }
    if (!up && nowMs - _wifiAttemptMs >= WIFI_RETRY_MS) {
      _wifiAttemptMs = nowMs;
      Serial.println(_placeholderCreds ? "[net] Wi-Fi: no credentials (see secrets_template.h)" : "[net] Wi-Fi reconnecting...");
      WiFi.reconnect();
    }
  }

  // ── Clock (TLS certificate validation needs real time) ───────────────────
  void serviceClock(uint32_t nowMs) {
    (void)nowMs;
    if (_wifiUp && !_ntpStarted) {
      configTzTime(TIMEZONE_POSIX, NTP_SERVER_1, NTP_SERVER_2);
      _ntpStarted = true;
    }
    if (_timeSynced && strcmp(_timeSource, "ntp") == 0) return;
    if (!_timeSynced && _ntpStarted && time(nullptr) > 1700000000) {
      _timeSynced = true; strcopy(_timeSource, sizeof _timeSource, "ntp");
      Serial.printf("[net] clock synced via NTP: %lu\n", (unsigned long)time(nullptr));
      return;
    }
    time_t g;
    if (!_timeSynced && _gps && _gps->epochUtc(g)) {           // no NTP yet → GPS time is good enough for TLS
      struct timeval tv = { g, 0 };
      settimeofday(&tv, nullptr);
      _timeSynced = true; strcopy(_timeSource, sizeof _timeSource, "gps");
      Serial.printf("[net] clock set from GPS: %lu\n", (unsigned long)g);
    }
  }

  // ── MQTT session ─────────────────────────────────────────────────────────
  void serviceMqtt(uint32_t nowMs) {
    if (!_wifiUp) { _mqttUp = false; return; }
    if (_mqtt.connected()) {
      _mqtt.loop();
      _lastOnlineMs = nowMs; _everOnline = true;
      return;
    }
    if (_mqttUp) {
      _mqttUp = false;
      Serial.printf("[net] MQTT disconnected (rc=%d)\n", _mqtt.state());
      _nextMqttAttemptMs = nowMs + _backoffMs;
    }
#if MQTT_USE_TLS && !MQTT_TLS_INSECURE
    if (!_timeSynced && nowMs - _wifiUpSinceMs < NTP_WAIT_BEFORE_TLS_MS) return;   // wait for a valid clock
#endif
    if ((int32_t)(nowMs - _nextMqttAttemptMs) < 0) return;

    char will[96];
    snprintf(will, sizeof will, "{\"device_id\":\"%s\",\"online\":false}", g_deviceId);
    const char* user = MQTT_USERNAME[0] ? MQTT_USERNAME : nullptr;
    const char* pass = MQTT_PASSWORD[0] ? MQTT_PASSWORD : nullptr;
    Serial.printf("[net] MQTT connecting to %s:%d ...\n", MQTT_HOST, (int)MQTT_PORT);
    const bool ok = _mqtt.connect(g_deviceId, user, pass, MQTT_TOPIC_DEVICE_STATUS, 1, true, will);
    if (ok) {
      _mqttUp = true; _everOnline = true; _lastOnlineMs = nowMs;
      _backoffMs = MQTT_RECONNECT_MIN_MS;
      _mqtt.subscribe(MQTT_TOPIC_ALERTS, 1);
      publishOnline(nowMs);
      _publishNow = true;
      Serial.println("[net] MQTT connected, subscribed to " MQTT_TOPIC_ALERTS);
    } else {
      Serial.printf("[net] MQTT connect failed rc=%d (retry in %lu ms)\n", _mqtt.state(), (unsigned long)_backoffMs);
      _nextMqttAttemptMs = nowMs + _backoffMs;
      _backoffMs = _backoffMs * 2 > MQTT_RECONNECT_MAX_MS ? MQTT_RECONNECT_MAX_MS : _backoffMs * 2;
    }
  }

  static void mqttTrampoline(char* topic, uint8_t* payload, unsigned int len) {
    if (s_instance) s_instance->onMessage(topic, payload, len);
  }

  // ── Incoming alerts (backend → band) ─────────────────────────────────────
  void onMessage(const char* topic, const uint8_t* payload, unsigned int len) {
    if (strcmp(topic, MQTT_TOPIC_ALERTS) != 0) return;
    NlwJsonDoc doc;
    const DeserializationError err = deserializeJson(doc, (const char*)payload, len);
    if (err) { Serial.printf("[net] alert JSON error: %s\n", err.c_str()); return; }

    const char* source = doc["source"] | "backend";
    if (strcmp(source, "device") == 0) return;                       // our own event echoed back
    const char* target = doc["device_id"] | "";
    if (target[0] && strcmp(target, g_deviceId) != 0) return;        // addressed to another band

    AlertState a;
    memset(&a, 0, sizeof a);
    strcopy(a.condition, sizeof a.condition, doc["condition"] | "Alert");
    strcopy(a.ensemble,  sizeof a.ensemble,  doc["ensemble"]  | "");

    // Severity: explicit field, otherwise derived from the pipeline's ensemble label
    if (!doc["severity"].isNull()) {
      strcopy(a.severity, sizeof a.severity, doc["severity"] | "info");
    } else if (strcmp(a.ensemble, "High Confidence Anomaly") == 0) {
      strcopy(a.severity, sizeof a.severity, "high");
    } else if (strcmp(a.ensemble, "Low Confidence Anomaly") == 0) {
      strcopy(a.severity, sizeof a.severity, "medium");
    } else if (strcmp(a.condition, "Normal") == 0 || strcmp(a.ensemble, "Normal") == 0) {
      return;                                                        // nothing to show
    } else {
      strcopy(a.severity, sizeof a.severity, "info");
    }

    // Message: explicit, else the LLM advice the pipeline attaches
    const char* msg = doc["message"] | "";
    if (!msg[0]) msg = doc["llm_advice"]["advice"] | "";
    if (!msg[0]) msg = doc["llm_advice"]["explanation"] | "";
    strcopy(a.message, sizeof a.message, msg);

    a.requireAck = doc["require_ack"] | (strcmp(a.severity, "critical") == 0);
    a.ttlMs      = (uint32_t)(doc["ttl_s"] | ALERT_DISPLAY_S) * 1000UL;
    if (a.requireAck && a.ttlMs < (uint32_t)ACK_WINDOW_S * 1000UL) a.ttlMs = (uint32_t)ACK_WINDOW_S * 1000UL;
    a.receivedMs = millis();
    a.id = ++_alertCounter;
    publishAlert(a);
    Serial.printf("[net] alert #%lu: %s (%s) ack=%d \"%s\"\n", (unsigned long)a.id, a.condition, a.severity, (int)a.requireAck, a.message);
  }

  // ── Telemetry (band → backend) ───────────────────────────────────────────
  static void ipToStr(const IPAddress& ip, char* out, size_t n) {
    snprintf(out, n, "%u.%u.%u.%u", (unsigned)ip[0], (unsigned)ip[1], (unsigned)ip[2], (unsigned)ip[3]);
  }
  static double rnd(double v, int decimals) {
    const double p = pow(10.0, decimals);
    return llround(v * p) / p;
  }
  static float pick(bool known, float v, float neutral) {
    if (known) return v;
    return PUBLISH_NEUTRAL_WHEN_MISSING ? neutral : 0.0f;
  }

  void fillGps(JsonObject g) {
    LinkStatus l = snapshotLink();
    g["fix"] = l.gpsFix;
    if (l.gpsFix) {
      g["lat"]   = rnd(l.lat, 6);
      g["lon"]   = rnd(l.lon, 6);
      g["age_s"] = l.gpsAgeMs / 1000;
    }
    g["sats"] = l.sats;
    g["hdop"] = rnd(l.hdop, 1);
  }

  void publishTelemetry(uint32_t nowMs) {
    const Telemetry t = snapshotTelemetry();
    NlwJsonDoc doc;
    doc["device_id"] = g_deviceId;
    doc["seq"]       = ++_seq;
    doc["ts"]        = (uint32_t)epochNow();
    doc["uptime_ms"] = nowMs;

    // ── Features named exactly like the training columns (pipeline.py) ──
    const bool hrKnown   = t.heartRate > 0;
    const bool hrvKnown  = t.hrv > 0;
    const bool spo2Known = t.spo2 > 0;
    doc["Heart_Rate"]       = rnd(pick(hrKnown,   t.heartRate, 72.0f), 1);
    doc["HRV"]              = rnd(pick(hrvKnown,  t.hrv,       50.0f), 1);
    doc["Blood_Oxygen"]     = rnd(pick(spo2Known, t.spo2,      97.0f), 1);
    doc["Body_Temperature"] = rnd(pick(t.tempValid, t.bodyTempC, 36.6f), 2);
    doc["GSR_Value"]        = rnd(pick(t.gsrPresent, t.gsrUs,  0.5f), 3);
    doc["Sweat_Response"]   = rnd(pick(t.gsrPresent, t.sweat,  0.2f), 3);
    doc["Step_Count"]       = t.stepsWindow;
    doc["Accel_X"] = rnd(pick(t.imuPresent, t.ax, 0.0f), 3);
    doc["Accel_Y"] = rnd(pick(t.imuPresent, t.ay, 0.0f), 3);
    doc["Accel_Z"] = rnd(pick(t.imuPresent, t.az, 1.0f), 3);
    doc["Gyro_X"]  = rnd(t.gx, 3);
    doc["Gyro_Y"]  = rnd(t.gy, 3);
    doc["Gyro_Z"]  = rnd(t.gz, 3);

    // ── Extra edge features / context ──
    doc["Edge_Activity"]     = t.edgeActivity;
    doc["Stress_Score"]      = rnd(t.stressScore, 3);
    doc["Accel_Var"]         = rnd(t.accelVar, 5);
    doc["Gyro_Var"]          = rnd(t.gyroVar, 5);
    doc["Motion_Freq_Hz"]    = rnd(t.motionFreqHz, 2);
    doc["Impact_G_Max"]      = rnd(t.impactGMax, 2);
    doc["Steps_Total"]       = t.stepsTotal;
    doc["Cadence_SPM"]       = rnd(t.cadenceSpm, 0);
    doc["Perfusion_Index"]   = rnd(t.perfusionPct, 2);
    if (t.thermoPresent) {
      doc["Skin_Temperature"]    = rnd(t.skinTempC, 2);
      doc["Ambient_Temperature"] = rnd(t.ambientTempC, 2);
    }
    if (t.batteryV > 0) doc["battery_v"] = rnd(t.batteryV, 2);
    doc["rssi"] = (int)WiFi.RSSI();

    JsonObject flags = NLW_NESTED(doc, "flags");
    flags["ppg_contact"] = t.ppgContact;
    flags["hr_valid"]    = t.hrValid;
    flags["spo2_valid"]  = t.spo2Valid;
    flags["temp_valid"]  = t.tempValid;
    flags["gsr_contact"] = t.gsrContact;

    JsonObject sensors = NLW_NESTED(doc, "sensors");
    sensors["ppg"]    = t.ppgPresent;
    sensors["imu"]    = t.imuPresent;
    sensors["gsr"]    = t.gsrPresent;
    sensors["thermo"] = t.thermoPresent;
    sensors["gps"]    = _gps && _gps->present();

    JsonObject safety = NLW_NESTED(doc, "safety");
    safety["state"]  = safetyStateName(t.safety);
    if (t.safety != SAFETY_IDLE) safety["reason"] = t.safetyReason;

    fillGps(NLW_NESTED(doc, "gps"));

    const size_t n = serializeJson(doc, _txBuf, sizeof _txBuf);
    if (n >= sizeof(_txBuf) - 1) { Serial.println("[net] telemetry JSON truncated — raise MQTT_BUFFER_BYTES"); _publishFailures++; return; }
    if (_mqtt.publish(MQTT_TOPIC_SENSORS, _txBuf)) {
      _lastPublishMs = nowMs;
    } else {
      _publishFailures++;
      Serial.printf("[net] publish failed (%u bytes, rc=%d)\n", (unsigned)n, _mqtt.state());
    }
  }

  void publishOnline(uint32_t nowMs) {
    const Telemetry t = snapshotTelemetry();
    NlwJsonDoc doc;
    doc["device_id"] = g_deviceId;
    doc["online"]    = true;
    doc["fw"]        = FIRMWARE_VERSION;
    char ip[16]; ipToStr(WiFi.localIP(), ip, sizeof ip);
    doc["ip"]        = ip;
    doc["rssi"]      = (int)WiFi.RSSI();
    doc["ts"]        = (uint32_t)epochNow();
    doc["uptime_ms"] = nowMs;
    doc["publish_interval_ms"] = PUBLISH_INTERVAL_MS;
    JsonObject sensors = NLW_NESTED(doc, "sensors");
    sensors["ppg"] = t.ppgPresent; sensors["imu"] = t.imuPresent; sensors["gsr"] = t.gsrPresent;
    sensors["thermo"] = t.thermoPresent; sensors["gps"] = _gps && _gps->present();
    char buf[384];
    serializeJson(doc, buf, sizeof buf);
    _mqtt.publish(MQTT_TOPIC_DEVICE_STATUS, buf, true);
  }

  // ── Device events → outbox → MQTT_TOPIC_ALERTS ───────────────────────────
  void drainEvents(uint32_t nowMs) {
    DeviceEvent e;
    while (takeEvent(e)) {
      int slot = -1;
      for (int i = 0; i < EVENT_OUTBOX_SIZE; i++) if (!_outbox[i].used) { slot = i; break; }
      if (slot < 0) {                                       // full: evict the oldest non-critical entry
        for (int i = 0; i < EVENT_OUTBOX_SIZE; i++) if (_outbox[i].ev.type != EVT_EMERGENCY) { slot = i; break; }
        if (slot < 0) slot = 0;
        Serial.println("[net] outbox full — dropping an older event");
      }
      _outbox[slot].used = true;
      _outbox[slot].createdMs = nowMs;
      _outbox[slot].ev = e;
      _outbox[slot].snap = snapshotTelemetry();
    }
  }

  void serviceOutbox(uint32_t nowMs) {
    for (int i = 0; i < EVENT_OUTBOX_SIZE; i++) {
      PendingEvent& p = _outbox[i];
      if (!p.used) continue;
      const uint32_t ttl = p.ev.type == EVT_EMERGENCY ? EVENT_OUTBOX_TTL_MS : 60000UL;
      if (nowMs - p.createdMs > ttl) { Serial.printf("[net] event %s expired unsent\n", eventName(p.ev.type)); p.used = false; continue; }
      if (!_mqtt.connected()) continue;
      buildEventJson(p.ev, p.snap, _txBuf, sizeof _txBuf);
      if (_mqtt.publish(MQTT_TOPIC_ALERTS, _txBuf)) {
        Serial.printf("[net] event published: %s (%s)\n", eventName(p.ev.type), p.ev.reason);
        p.used = false;
      } else {
        _publishFailures++;
        return;                                             // try again on the next pass
      }
    }
  }

  static const char* eventName(EventType t) {
    switch (t) {
      case EVT_PROMPT_STARTED: return "PROMPT_STARTED";
      case EVT_ACKNOWLEDGED:   return "ACKNOWLEDGED";
      case EVT_EMERGENCY:      return "EMERGENCY";
      case EVT_USER_RESPONDED: return "USER_RESPONDED";
    }
    return "UNKNOWN";
  }

  static void humanMessage(const DeviceEvent& e, char* out, size_t n) {
    const bool fall = strncmp(e.reason, "FALL", 4) == 0;
    const bool sos  = strcmp(e.reason, "SOS_BUTTON") == 0;
    const char* cond = strncmp(e.reason, "BACKEND:", 8) == 0 ? e.reason + 8 : e.reason;
    switch (e.type) {
      case EVT_PROMPT_STARTED:
        if (fall) snprintf(out, n, "Possible fall detected (%s confidence). Asking the wearer to confirm within %u s.", e.confidence, (unsigned)e.ackWindowS);
        else      snprintf(out, n, "Health alert '%s' shown on the band. Waiting %u s for the wearer to confirm.", cond, (unsigned)e.ackWindowS);
        break;
      case EVT_ACKNOWLEDGED:   snprintf(out, n, "Wearer pressed 'I'm OK' — alert cancelled."); break;
      case EVT_USER_RESPONDED: snprintf(out, n, "Wearer responded after the emergency was raised."); break;
      case EVT_EMERGENCY:
        if (sos)       snprintf(out, n, "SOS button held by the wearer. Immediate assistance requested.");
        else if (fall) snprintf(out, n, "Fall detected and NOT acknowledged within %u s. Wearer may be unconscious.", (unsigned)e.ackWindowS);
        else           snprintf(out, n, "Critical alert '%s' NOT acknowledged within %u s.", cond, (unsigned)e.ackWindowS);
        break;
    }
  }

  void buildEventJson(const DeviceEvent& e, const Telemetry& t, char* out, size_t outSize) {
    NlwJsonDoc doc;
    doc["source"]    = "device";
    doc["device_id"] = g_deviceId;
    doc["event"]     = eventName(e.type);
    doc["severity"]  = e.type == EVT_EMERGENCY ? "critical" : e.type == EVT_PROMPT_STARTED ? "high" : "info";
    doc["reason"]    = e.reason;
    doc["trigger"]   = e.trigger;
    if (e.confidence[0]) doc["confidence"] = e.confidence;
    if (e.impactG > 0) {
      doc["impact_g"] = rnd(e.impactG, 2);
      doc["orientation_change_deg"] = rnd(e.orientDeg, 0);
    }
    if (e.type == EVT_PROMPT_STARTED) doc["ack_window_s"] = e.ackWindowS;
    doc["ts"]        = (uint32_t)epochNow();
    doc["uptime_ms"] = e.uptimeMs;
    char msg[160];
    humanMessage(e, msg, sizeof msg);
    doc["message"] = msg;

    JsonObject v = NLW_NESTED(doc, "vitals");
    v["heart_rate"]  = rnd(t.heartRate, 1);
    v["spo2"]        = rnd(t.spo2, 1);
    v["temperature"] = rnd(t.bodyTempC, 2);
    v["hrv"]         = rnd(t.hrv, 1);
    v["stress"]      = rnd(t.stressScore, 3);
    v["hr_valid"]    = t.hrValid;
    v["ppg_contact"] = t.ppgContact;

    fillGps(NLW_NESTED(doc, "gps"));
    LinkStatus l = snapshotLink();
    if (l.gpsFix) {
      char url[64];
      snprintf(url, sizeof url, "https://maps.google.com/?q=%.6f,%.6f", l.lat, l.lon);
      doc["maps_url"] = url;
    }
    serializeJson(doc, out, outSize);
  }

  // ── Shared snapshot for the display / other task ─────────────────────────
  void updateLinkSnapshot(uint32_t nowMs) {
    (void)nowMs;
    LinkStatus l;
    memset(&l, 0, sizeof l);
    l.wifiConnected = _wifiUp;
    l.rssi = _wifiUp ? (int8_t)WiFi.RSSI() : 0;
    if (_wifiUp) ipToStr(WiFi.localIP(), l.ip, sizeof l.ip);
    l.mqttConnected   = _mqtt.connected();
    l.mqttState       = _mqtt.state();
    l.lastPublishMs   = _lastPublishMs;
    l.seq             = _seq;
    l.publishFailures = _publishFailures;
    l.timeSynced      = _timeSynced;
    strcopy(l.timeSource, sizeof l.timeSource, _timeSource);
    if (_gps) _gps->fill(l);
    publishLinkSnapshot(l);
  }

  // ── Connectivity watchdog ────────────────────────────────────────────────
  void watchdog(uint32_t nowMs) {
#if CONNECTIVITY_WATCHDOG_MIN > 0
    if (!_everOnline) return;                              // never connected → reboot would not help
    if (nowMs - _lastOnlineMs < (uint32_t)CONNECTIVITY_WATCHDOG_MIN * 60000UL) return;
    const Telemetry t = snapshotTelemetry();
    if (t.safety != SAFETY_IDLE) return;                   // never reboot in the middle of an alert
    Serial.println("[net] offline for too long — restarting");
    delay(200);
    ESP.restart();
#else
    (void)nowMs;
#endif
  }
};

NetLink* NetLink::s_instance = nullptr;

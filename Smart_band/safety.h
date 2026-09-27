/**
 * NeuroLink Wear — safety & escalation state machine
 * ---------------------------------------------------
 *  Implements steps 1–4 of the emergency workflow on the band itself:
 *
 *    IDLE ──fall / critical backend alert──▶ PROMPT ("Are you OK?", countdown)
 *      │                                       │ short press → ACKNOWLEDGED → RESOLVED → IDLE
 *      │ long press (SOS)                      │ timeout / long press
 *      ▼                                       ▼
 *    ESCALATED (emergency packet published with vitals + GPS)
 *      │ short press → USER_RESPONDED → RESOLVED → IDLE
 *      │ long press  → resend emergency (rate limited)
 *
 *  Button (BOOT / GPIO0, active LOW):
 *    • short press : "I'm OK" during an alert, otherwise cycles the OLED pages
 *    • hold 3 s    : manual SOS
 *
 *  Events are pushed to the network task, which attaches GPS / vitals and
 *  publishes them on MQTT_TOPIC_ALERTS with "source":"device".
 */
#pragma once

#include <Arduino.h>
#include <stdio.h>
#include "config.h"
#include "shared_state.h"
#include "imu.h"

class SafetyManager {
public:
  void begin() {
    pinMode(PIN_BUTTON, INPUT_PULLUP);
#if PIN_HAPTIC >= 0
    pinMode(PIN_HAPTIC, OUTPUT);
    digitalWrite(PIN_HAPTIC, LOW);
#endif
    _btnRaw = _btnStable = readButton();     // ignore a button held during boot
  }

  /** Call every sensor-loop iteration. */
  void service(uint32_t nowMs, ImuSensor& imu, const AlertState& alert) {
    bool shortPress = false, longPress = false;
    pollButton(nowMs, shortPress, longPress);
    if (_simShort) { shortPress = true; _simShort = false; }
    if (_simLong)  { longPress  = true; _simLong  = false; }

    // Fall from the IMU (or the serial-console demo hook)
    ImuSensor::FallEvent fall = { false, 0, 0, false, "low" };
    bool haveFall = imu.takeFallEvent(fall);
    if (_simFall) { _simFall = false; haveFall = true; fall = { true, 4.2f, 75.0f, true, "high" }; }
    if (haveFall && confidenceRank(fall.confidence) < FALL_PROMPT_MIN_CONFIDENCE) haveFall = false;

    // New backend alert that asks for a local confirmation
    const bool newBackendPrompt = alert.id != 0 && alert.id != _lastAlertId && alert.requireAck;
    _lastAlertId = alert.id;

    switch (_state) {
      case SAFETY_IDLE:
        if (longPress)              { setCause("SOS_BUTTON", "", 0, 0); escalate(nowMs, "sos_button"); }
        else if (haveFall)          { setCause("FALL", fall.confidence, fall.impactG, fall.orientDeg); startPrompt(nowMs); }
        else if (newBackendPrompt)  {
          char cause[32];
          snprintf(cause, sizeof cause, "BACKEND:%s", alert.condition);
          setCause(cause, "", 0, 0);
          startPrompt(nowMs);
        }
        else if (shortPress)        _pageCycle = true;
        break;

      case SAFETY_PROMPT:
        if (longPress)                                   escalate(nowMs, "sos_button");
        else if (shortPress)                             resolve(nowMs, EVT_ACKNOWLEDGED);
        else if ((int32_t)(nowMs - _deadlineMs) >= 0)    escalate(nowMs, "timeout");
        else if (nowMs - _lastHapticMs >= 1000)          { _lastHapticMs = nowMs; hapticPulse(nowMs, HAPTIC_PULSE_MS); }
        break;

      case SAFETY_ESCALATED:
        if (shortPress)                                              resolve(nowMs, EVT_USER_RESPONDED);
        else if (longPress && nowMs - _escalatedMs >= SOS_REPEAT_MIN_MS) escalate(nowMs, "sos_button");
        break;

      case SAFETY_RESOLVED:
        if (nowMs - _resolvedMs >= RESOLVED_SCREEN_MS) _state = SAFETY_IDLE;
        break;
    }

#if PIN_HAPTIC >= 0
    digitalWrite(PIN_HAPTIC, (int32_t)(nowMs - _hapticUntil) < 0 ? HIGH : LOW);
#endif
  }

  SafetyState state() const        { return _state; }
  const char* cause() const        { return _cause; }
  uint32_t    deadlineMs() const   { return _deadlineMs; }
  uint32_t    escalations() const  { return _escalations; }

  /** Short press while idle → the display should switch page. */
  bool takePageCycle() { const bool c = _pageCycle; _pageCycle = false; return c; }

  void fill(Telemetry& t) const {
    t.safety = _state;
    t.promptDeadlineMs = _deadlineMs;
    strcopy(t.safetyReason, sizeof t.safetyReason, _cause);
  }

  // Demo hooks (serial console): behave exactly like the real triggers.
  void simulateFall()        { _simFall  = true; }
  void simulateButtonPress() { _simShort = true; }
  void simulateSos()         { _simLong  = true; }

private:
  SafetyState _state = SAFETY_IDLE;
  char     _cause[32] = "";
  char     _confidence[8] = "";
  float    _impactG = 0, _orientDeg = 0;
  uint32_t _deadlineMs = 0, _escalatedMs = 0, _resolvedMs = 0, _escalations = 0;
  uint32_t _lastAlertId = 0;
  bool     _pageCycle = false;
  bool     _simFall = false, _simShort = false, _simLong = false;

  // Button
  bool     _btnRaw = false, _btnStable = false, _longFired = false;
  uint32_t _btnChangeMs = 0, _pressStartMs = 0;

  // Haptics
  uint32_t _hapticUntil = 0, _lastHapticMs = 0;

  static int confidenceRank(const char* c) {
    if (!c) return 0;
    if (strcmp(c, "high") == 0) return 2;
    if (strcmp(c, "medium") == 0) return 1;
    return 0;
  }

  bool readButton() const { return digitalRead(PIN_BUTTON) == LOW; }

  void pollButton(uint32_t nowMs, bool& shortPress, bool& longPress) {
    const bool raw = readButton();
    if (raw != _btnRaw) { _btnRaw = raw; _btnChangeMs = nowMs; }
    if (raw != _btnStable && (nowMs - _btnChangeMs) >= BUTTON_DEBOUNCE_MS) {
      _btnStable = raw;
      if (raw) { _pressStartMs = nowMs; _longFired = false; }
      else if (!_longFired) shortPress = true;
    }
    if (_btnStable && !_longFired && (nowMs - _pressStartMs) >= SOS_LONG_PRESS_MS) {
      _longFired = true;
      longPress = true;
    }
  }

  void setCause(const char* cause, const char* confidence, float impactG, float orientDeg) {
    strcopy(_cause, sizeof _cause, cause);
    strcopy(_confidence, sizeof _confidence, confidence);
    _impactG = impactG; _orientDeg = orientDeg;
  }

  DeviceEvent makeEvent(EventType type, uint32_t nowMs, const char* trigger) const {
    DeviceEvent e;
    memset(&e, 0, sizeof e);
    e.type = type;
    strcopy(e.reason, sizeof e.reason, _cause);
    strcopy(e.trigger, sizeof e.trigger, trigger);
    strcopy(e.confidence, sizeof e.confidence, _confidence);
    e.impactG = _impactG; e.orientDeg = _orientDeg;
    e.ackWindowS = ACK_WINDOW_S;
    e.uptimeMs = nowMs;
    return e;
  }

  void startPrompt(uint32_t nowMs) {
    _state = SAFETY_PROMPT;
    _deadlineMs = nowMs + (uint32_t)ACK_WINDOW_S * 1000UL;
    _lastHapticMs = 0;
    hapticPulse(nowMs, 600);
    postEvent(makeEvent(EVT_PROMPT_STARTED, nowMs, "detector"));
    Serial.printf("[safety] PROMPT started (%s) — %u s to acknowledge\n", _cause, (unsigned)ACK_WINDOW_S);
  }

  void escalate(uint32_t nowMs, const char* trigger) {
    _state = SAFETY_ESCALATED;
    _escalatedMs = nowMs;
    _escalations++;
    hapticPulse(nowMs, 1500);
    postEvent(makeEvent(EVT_EMERGENCY, nowMs, trigger));
    Serial.printf("[safety] EMERGENCY (%s, trigger=%s)\n", _cause, trigger);
  }

  void resolve(uint32_t nowMs, EventType evt) {
    _state = SAFETY_RESOLVED;
    _resolvedMs = nowMs;
    _hapticUntil = 0;
    postEvent(makeEvent(evt, nowMs, "button"));
    Serial.printf("[safety] %s by wearer (%s)\n", evt == EVT_ACKNOWLEDGED ? "ACKNOWLEDGED" : "USER_RESPONDED", _cause);
  }

  void hapticPulse(uint32_t nowMs, uint32_t ms) { _hapticUntil = nowMs + ms; }
};

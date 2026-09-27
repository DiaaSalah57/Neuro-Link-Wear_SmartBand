/**
 * NeuroLink Wear — GSR module (skin conductance)
 * ----------------------------------------------
 *  Reads the GSR analog output on an ADC1 pin (ADC2 is unavailable while
 *  Wi-Fi is active), converts it to skin conductance in micro-siemens (the
 *  unit of GSR_Value in the training data, 0.1–20 µS) and derives:
 *   • Sweat_Response — conductance scaled by cardiovascular load (proxy for
 *                      the synthetic training feature)
 *   • Stress_Score   — same normalisation as the backend pipeline
 *                      (GSR up + HRV down ⇒ sympathetic arousal)
 */
#pragma once

#include <Arduino.h>
#include "config.h"
#include "shared_state.h"

class GsrSensor {
public:
  void begin() {
    pinMode(PIN_GSR_ADC, INPUT);
    analogSetPinAttenuation(PIN_GSR_ADC, ADC_11db);   // full 0–3.3 V range
    _present = true;
  }

  void service(uint32_t nowMs) {
    if (!_present || nowMs - _lastMs < GSR_SAMPLE_MS) return;
    _lastMs = nowMs;
    uint32_t sum = 0;
    for (uint8_t i = 0; i < 8; i++) sum += analogReadMilliVolts(PIN_GSR_ADC);   // calibrated mV, 8× oversampled
    const float mv = sum / 8.0f;
    _raw = (uint16_t)analogRead(PIN_GSR_ADC);
    _mv  = _init ? _mv + (mv - _mv) * 0.25f : mv;
    _init = true;
    processMillivolts(_mv);
  }

  /** mV → µS. Public for PC unit tests. */
  void processMillivolts(float mv) {
    float us;
#if GSR_MODE == 1
    // Grove GSR: output rests at Vcc/2 with open electrodes and falls as skin
    // conductance rises. Formula from the Seeed wiki (10-bit / 5 V reference),
    // applied on a supply-normalised scale so it also holds at 3.3 V.
    const float s = mv / (float)GSR_SUPPLY_MV * 1024.0f;
    if (s >= 508.0f) { _contact = false; _us = GSR_MIN_US; return; }
    const float rOhm = ((1024.0f + 2.0f * s) * 10000.0f) / (512.0f - s);
    us = 1.0e6f / rOhm;
    _contact = true;
#else
    // Plain electrode divider: linear map of the voltage onto 0.1–20 µS
    float k = (mv - GSR_LINEAR_MIN_MV) / (float)(GSR_LINEAR_MAX_MV - GSR_LINEAR_MIN_MV);
    if (k < 0) k = 0;
    if (k > 1) k = 1;
    us = 0.1f + k * 19.9f;
    _contact = mv > GSR_LINEAR_MIN_MV * 0.5f;
#endif
    if (us < GSR_MIN_US) us = GSR_MIN_US;
    if (us > GSR_MAX_US) us = GSR_MAX_US;
    _us = us;
  }

  bool  present() const  { return _present; }
  bool  contact() const  { return _contact; }
  float microSiemens() const { return _us; }
  float millivolts() const   { return _mv; }

  /** Needs t.heartRate / t.hrValid / t.hrv → call after PpgSensor::fill(). */
  void fill(Telemetry& t) const {
    t.gsrPresent = _present;
    t.gsrContact = _contact;
    t.gsrRaw = _raw;
    t.gsrMv  = _mv;
    t.gsrUs  = _us;

    float gsrN = (_us - STATS_GSR_MIN) / (STATS_GSR_MAX - STATS_GSR_MIN);
    gsrN = clamp01(gsrN);
    if (t.hrValid && t.hrv > 0) {
      const float hrvN = clamp01((t.hrv - STATS_HRV_MIN) / (STATS_HRV_MAX - STATS_HRV_MIN));
      t.stressScore = (gsrN + (1.0f - hrvN)) * 0.5f;      // identical to pipeline.py
    } else {
      t.stressScore = gsrN;                                // no HRV yet → conductance only
    }

    float hrFactor = t.hrValid ? (t.heartRate - 40.0f) / 100.0f : 0.5f;
    if (hrFactor < 0.2f) hrFactor = 0.2f;
    if (hrFactor > 1.2f) hrFactor = 1.2f;
    t.sweat = _us * hrFactor;
  }

  static const char* stressLabel(float score) {
    return score >= STRESS_HIGH_THRESHOLD ? "HIGH" : score >= STRESS_MED_THRESHOLD ? "MED" : "LOW";
  }

private:
  bool     _present = false, _init = false, _contact = false;
  uint32_t _lastMs = 0;
  uint16_t _raw = 0;
  float    _mv = 0, _us = GSR_MIN_US;

  static float clamp01(float v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }
};

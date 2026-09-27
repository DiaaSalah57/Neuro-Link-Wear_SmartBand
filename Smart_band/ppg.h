/**
 * NeuroLink Wear — PPG module (MAX30102 / MAX30105)
 * --------------------------------------------------
 *  • Drains the sensor FIFO (Red + IR at 100 samples/s)
 *  • Beat detection: SparkFun/Maxim PBA algorithm (checkForBeat)
 *  • Heart rate     : mean of the last 4 valid inter-beat intervals
 *  • HRV            : RMSSD over the last HRV_WINDOW_BEATS intervals
 *  • SpO2           : ratio-of-ratios (AC/DC of Red vs IR) with Maxim's
 *                     empirical calibration curve — an estimate, not clinical
 *  • Contact        : IR level with hysteresis
 *
 * Inter-beat intervals are measured in *samples* (10 ms each) rather than
 * millis() so that scheduling jitter does not pollute the HRV figure.
 */
#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "MAX30105.h"
#include "heartRate.h"
#include "config.h"
#include "shared_state.h"

class PpgSensor {
public:
  static constexpr float kSamplePeriodMs = 1000.0f * PPG_SAMPLE_AVERAGE / PPG_SAMPLE_RATE;   // 10 ms

  bool begin(TwoWire& wire) {
    _present = _sensor.begin(wire, I2C_SPEED_FAST, I2C_ADDR_MAX3010X);
    if (!_present) return false;
    // ledMode 2 = Red + IR (green is not needed and only exists on the MAX30105)
    _sensor.setup(PPG_LED_BRIGHTNESS, PPG_SAMPLE_AVERAGE, 2, PPG_SAMPLE_RATE, PPG_PULSE_WIDTH, PPG_ADC_RANGE);
    _sensor.setPulseAmplitudeGreen(0);
    _sensor.clearFIFO();
    return true;
  }

  /** Drain the FIFO. Call as often as possible — the SparkFun driver only
   *  buffers 4 samples, i.e. 40 ms at 100 samples/s. */
  void service(uint32_t nowMs) {
    if (!_present) return;
    _sensor.check();
    while (_sensor.available()) {
      const uint32_t ir  = _sensor.getFIFOIR();
      const uint32_t red = _sensor.getFIFORed();
      _sensor.nextSample();
      processSample(nowMs, ir, red);
    }
  }

  /** One Red/IR sample. Public so it can be unit-tested on a PC. */
  void processSample(uint32_t nowMs, uint32_t ir, uint32_t red) {
    _sampleIdx++;
    _ir = ir; _red = red;

    // Contact detection with hysteresis (on above MIN, off below 80 % of MIN)
    const bool contact = _contact ? (ir > PPG_CONTACT_IR_MIN * 8 / 10) : (ir > PPG_CONTACT_IR_MIN);
    if (contact != _contact) {
      _contact = contact;
      if (!contact) resetSignal();
    }
    if (!contact) return;

    // ── Beat detection ──
    if (checkForBeat((int32_t)ir)) onBeat(nowMs);

    // ── DC / AC trackers for SpO2 ──
    if (!_dcInit) {
      _irDc = ir; _redDc = red; _irAc2 = _redAc2 = 0.0; _dcInit = true;
    } else {
      const double kDc = 0.02, kAc = 0.01;                 // ≈0.5 s and ≈1 s time constants
      _irDc  += ((double)ir  - _irDc)  * kDc;
      _redDc += ((double)red - _redDc) * kDc;
      const double irAc = (double)ir - _irDc, redAc = (double)red - _redDc;
      _irAc2  += (irAc  * irAc  - _irAc2)  * kAc;
      _redAc2 += (redAc * redAc - _redAc2) * kAc;
    }
    if (nowMs - _lastSpo2Ms >= 1000) { _lastSpo2Ms = nowMs; updateSpo2(nowMs); }
  }

  // ── Accessors ──
  bool     present() const            { return _present; }
  bool     contact() const            { return _contact; }
  bool     hrValid(uint32_t nowMs) const {
    return _contact && _ibiCount >= 2 && _lastValidHrMs != 0 && (nowMs - _lastValidHrMs) < PPG_HR_TIMEOUT_MS;
  }
  bool     spo2Valid(uint32_t nowMs) const { return _spo2Valid && hrValid(nowMs); }
  float    bpm() const                { return _bpm; }
  float    rmssd() const              { return _rmssd; }
  float    spo2() const               { return _spo2; }
  float    perfusion() const          { return _perf; }
  uint32_t ir() const                 { return _ir; }
  uint32_t red() const                { return _red; }
  uint32_t beatsTotal() const         { return _beatsTotal; }
  uint32_t artifactsRejected() const  { return _artifacts; }
  /** True for 150 ms after each beat — drives the heart icon on the OLED. */
  bool     beatFlash(uint32_t nowMs) const { return _lastBeatMs != 0 && (nowMs - _lastBeatMs) < 150; }

  void fill(Telemetry& t, uint32_t nowMs) const {
    t.ppgPresent = _present;
    t.ppgContact = _contact;
    t.ir = _ir; t.red = _red;
    t.hrValid   = hrValid(nowMs);
    t.spo2Valid = spo2Valid(nowMs);
    // Keep repeating the last good value for a while after contact is lost
    // (flags tell the backend it is stale); after PPG_STALE_MS report 0.
    const bool recent = _lastValidHrMs != 0 && (nowMs - _lastValidHrMs) < PPG_STALE_MS;
    t.heartRate    = recent ? _bpm   : 0.0f;
    t.hrv          = recent ? _rmssd : 0.0f;
    t.spo2         = (recent && _lastSpo2ValidMs != 0) ? _spo2 : 0.0f;
    t.perfusionPct = _perf * 100.0f;
  }

private:
  MAX30105 _sensor;
  bool     _present = false;
  bool     _contact = false;
  uint32_t _ir = 0, _red = 0;
  uint32_t _sampleIdx = 0;

  // Beats / HRV
  uint32_t _lastBeatIdx = 0, _lastBeatMs = 0, _lastValidHrMs = 0;
  float    _ibi[HRV_WINDOW_BEATS] = {0};
  uint8_t  _ibiCount = 0, _ibiHead = 0;
  float    _bpm = 0, _rmssd = 0;
  uint32_t _beatsTotal = 0, _artifacts = 0;

  // SpO2
  bool     _dcInit = false, _spo2Valid = false;
  double   _irDc = 0, _redDc = 0, _irAc2 = 0, _redAc2 = 0;
  float    _spo2 = 0, _perf = 0;
  uint32_t _lastSpo2Ms = 0, _lastSpo2ValidMs = 0;

  void resetSignal() {
    _ibiCount = _ibiHead = 0;
    _lastBeatIdx = 0;
    _dcInit = false;
    _spo2Valid = false;
    _perf = 0;
  }

  /** k-th oldest stored interval (0 = oldest). */
  float ibiAt(uint8_t k) const {
    const uint8_t start = (_ibiCount < HRV_WINDOW_BEATS) ? 0 : _ibiHead;
    return _ibi[(start + k) % HRV_WINDOW_BEATS];
  }

  float medianRecent() const {
    uint8_t n = _ibiCount < 5 ? _ibiCount : 5;
    float v[5];
    for (uint8_t i = 0; i < n; i++) v[i] = ibiAt(_ibiCount - n + i);
    for (uint8_t i = 1; i < n; i++) {                       // insertion sort
      float x = v[i]; int j = i - 1;
      while (j >= 0 && v[j] > x) { v[j + 1] = v[j]; j--; }
      v[j + 1] = x;
    }
    return v[n / 2];
  }

  void onBeat(uint32_t nowMs) {
    const uint32_t gapSamples = _sampleIdx - _lastBeatIdx;
    const bool firstBeat = (_lastBeatIdx == 0) || gapSamples * kSamplePeriodMs > 3000.0f;
    _lastBeatIdx = _sampleIdx;
    _lastBeatMs  = nowMs;
    if (firstBeat) return;                                   // nothing to measure yet

    const float ibi = gapSamples * kSamplePeriodMs;
    if (ibi < 60000.0f / HR_MAX_BPM || ibi > 60000.0f / HR_MIN_BPM) return;   // impossible → ignore
    if (_ibiCount >= 3) {                                    // ectopic beat / motion artifact filter
      const float med = medianRecent();
      if (fabsf(ibi - med) > 0.35f * med) { _artifacts++; return; }
    }

    _ibi[_ibiHead] = ibi;
    _ibiHead = (_ibiHead + 1) % HRV_WINDOW_BEATS;
    if (_ibiCount < HRV_WINDOW_BEATS) _ibiCount++;
    _beatsTotal++;

    // Heart rate = 60000 / mean of the last (up to) 4 intervals
    const uint8_t n = _ibiCount < 4 ? _ibiCount : 4;
    float sum = 0;
    for (uint8_t i = 0; i < n; i++) sum += ibiAt(_ibiCount - 1 - i);
    _bpm = 60000.0f * n / sum;
    _lastValidHrMs = nowMs;

    if (_ibiCount >= 6) computeRmssd();
  }

  void computeRmssd() {
    float sumSq = 0; uint16_t n = 0;
    for (uint8_t i = 1; i < _ibiCount; i++) {
      const float d = ibiAt(i) - ibiAt(i - 1);
      sumSq += d * d; n++;
    }
    if (n) _rmssd = sqrtf(sumSq / n);
  }

  void updateSpo2(uint32_t nowMs) {
    if (!_dcInit || _irDc < 1000.0 || _redDc < 1000.0) { _spo2Valid = false; return; }
    const double irRms = sqrt(_irAc2), redRms = sqrt(_redAc2);
    _perf = (float)(irRms / _irDc);                           // perfusion index (AC/DC)
    if (_perf < SPO2_MIN_PERFUSION || redRms <= 0.0) { _spo2Valid = false; return; }

    const double R = (redRms / _redDc) / (irRms / _irDc);     // ratio of ratios
    if (R < 0.3 || R > 1.3) { _spo2Valid = false; return; }   // outside physiological range → artifact
    double spo2 = -45.060 * R * R + 30.354 * R + 94.845;      // Maxim empirical calibration
    if (spo2 > 100.0) spo2 = 100.0;
    if (spo2 < 70.0)  spo2 = 70.0;

    _spo2 = _spo2Valid ? (0.7f * _spo2 + 0.3f * (float)spo2) : (float)spo2;   // light smoothing
    _spo2Valid = hrValid(nowMs);                              // only trust SpO2 while a pulse is tracked
    if (_spo2Valid) _lastSpo2ValidMs = nowMs;
  }
};

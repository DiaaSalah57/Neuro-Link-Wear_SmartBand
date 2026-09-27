/**
 * NeuroLink Wear — IMU module (MPU6050, raw I2C — no extra libraries)
 * --------------------------------------------------------------------
 *  Sampled at 50 Hz. Produces:
 *   • accel (g) / gyro (rad/s)                → published raw for the models
 *   • 2-s rolling variance of |a| and |ω|     → tremor / activity context
 *   • dominant motion frequency (zero-crossings of the band-passed |a|)
 *   • pedometer with bout detection            → Step_Count (rolling 60 s)
 *   • deterministic fall detector:
 *        impact (|a| > FALL_IMPACT_G)  →  settle  →  immobility window
 *        confidence from free-fall before impact, impact size and the
 *        orientation change of the gravity vector across the event.
 *
 *  Also accepts MPU6500 / MPU9250 clones (identical basic register map).
 */
#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "config.h"
#include "shared_state.h"

class ImuSensor {
public:
  struct FallEvent {
    bool        pending;
    float       impactG;
    float       orientDeg;
    bool        freefall;
    const char* confidence;   // "high" | "medium" | "low"
  };

  static constexpr uint16_t kRingN   = MOTION_VAR_WINDOW_MS / IMU_SAMPLE_MS;   // 100 samples
  static constexpr uint8_t  kBinN    = STEP_WINDOW_MS / 1000;                   // 60 one-second bins
  static constexpr uint8_t  kOrientN = 4;                                       // 4 × 500 ms of posture history
  static constexpr float    kDegToRad = 0.01745329252f;
  static constexpr float    kAccelLsbPerG   = 2048.0f;   // ±16 g
  static constexpr float    kGyroLsbPerDps  = 16.4f;     // ±2000 °/s

  bool begin(TwoWire& wire) {
    _wire = &wire;
    const uint8_t candidates[2] = { I2C_ADDR_MPU6050, (uint8_t)(I2C_ADDR_MPU6050 | 0x01) };
    for (uint8_t i = 0; i < 2 && !_present; i++) {
      _addr = candidates[i];
      uint8_t who = 0;
      if (!readRegs(0x75, &who, 1)) continue;
      // 0x68 MPU6050 · 0x70 MPU6500 · 0x71 MPU9250 · 0x73 MPU9255 · 0x72/0x74 other clones
      if (who == 0x68 || who == 0x70 || who == 0x71 || who == 0x72 || who == 0x73 || who == 0x74) {
        _present = true; _whoAmI = who;
      }
    }
    if (!_present) return false;

    writeReg(0x6B, 0x80); delay(100);   // PWR_MGMT_1: device reset
    writeReg(0x6B, 0x01); delay(10);    // wake up, PLL with X gyro reference
    writeReg(0x19, 0x04);               // SMPLRT_DIV: 1 kHz / (1+4) = 200 Hz internal rate
    writeReg(0x1A, 0x03);               // CONFIG: DLPF ≈ 44 Hz accel / 42 Hz gyro
    writeReg(0x1B, 0x18);               // GYRO_CONFIG: ±2000 °/s
    writeReg(0x1C, 0x18);               // ACCEL_CONFIG: ±16 g (impacts of a fall can exceed 8 g)
    return true;
  }

  /** Read one sample. Call every IMU_SAMPLE_MS. */
  void service(uint32_t nowMs) {
    if (!_present) return;
    uint8_t b[14];
    if (!readRegs(0x3B, b, 14)) { _readErrors++; return; }
    const int16_t rax = (int16_t)((b[0]  << 8) | b[1]);
    const int16_t ray = (int16_t)((b[2]  << 8) | b[3]);
    const int16_t raz = (int16_t)((b[4]  << 8) | b[5]);
    const int16_t rgx = (int16_t)((b[8]  << 8) | b[9]);
    const int16_t rgy = (int16_t)((b[10] << 8) | b[11]);
    const int16_t rgz = (int16_t)((b[12] << 8) | b[13]);
    processSample(nowMs,
                  rax / kAccelLsbPerG, ray / kAccelLsbPerG, raz / kAccelLsbPerG,
                  rgx / kGyroLsbPerDps * kDegToRad, rgy / kGyroLsbPerDps * kDegToRad, rgz / kGyroLsbPerDps * kDegToRad);
  }

  /** Feed one sample (accel in g, gyro in rad/s). Public for PC unit tests. */
  void processSample(uint32_t nowMs, float ax, float ay, float az, float gx, float gy, float gz) {
    _ax = ax; _ay = ay; _az = az; _gx = gx; _gy = gy; _gz = gz;
    const float mag  = sqrtf(ax * ax + ay * ay + az * az);
    const float gmag = sqrtf(gx * gx + gy * gy + gz * gz);
    _accelMag = mag;

    if (!_init) {
      _gravX = ax; _gravY = ay; _gravZ = az; _magLp = mag; _dyn = 0; _init = true;
      for (uint8_t i = 0; i < kOrientN; i++) { _orientHist[i][0] = ax; _orientHist[i][1] = ay; _orientHist[i][2] = az; }
    }

    // Slow gravity estimate (posture)
    const float kg = 0.05f;
    _gravX += (ax - _gravX) * kg; _gravY += (ay - _gravY) * kg; _gravZ += (az - _gravZ) * kg;

    // Band-passed dynamic acceleration for the pedometer
    _magLp += (mag - _magLp) * 0.02f;     // ≈1 s baseline (removes gravity)
    _dyn   += ((mag - _magLp) - _dyn) * 0.35f;   // smooths sensor jitter

    // Rolling windows
    _magRing[_ringIdx]  = mag;
    _gyroRing[_ringIdx] = gmag;
    _dynRing[_ringIdx]  = _dyn;
    _ringIdx = (_ringIdx + 1) % kRingN;
    if (_ringCount < kRingN) _ringCount++;

    detectStep(nowMs);
    updateFallFsm(nowMs, mag, gmag);

    if (nowMs - _lastOrientMs >= 500) {   // posture history: oldest entry ≈ 2 s ago
      _lastOrientMs = nowMs;
      _orientHist[_orientIdx][0] = _gravX; _orientHist[_orientIdx][1] = _gravY; _orientHist[_orientIdx][2] = _gravZ;
      _orientIdx = (_orientIdx + 1) % kOrientN;
    }
  }

  /** Returns true once per detected fall and hands over the details. */
  bool takeFallEvent(FallEvent& out) {
    if (!_fall.pending) return false;
    out = _fall;
    _fall.pending = false;
    return true;
  }

  bool     present() const     { return _present; }
  uint8_t  whoAmI() const      { return _whoAmI; }
  uint32_t readErrors() const  { return _readErrors; }
  uint32_t stepsTotal() const  { return _stepsTotal; }

  void fill(Telemetry& t, uint32_t nowMs) {
    t.imuPresent = _present;
    t.ax = _ax; t.ay = _ay; t.az = _az; t.gx = _gx; t.gy = _gy; t.gz = _gz;
    t.accelMag = _accelMag;

    // Window statistics
    float aSum = 0, aSq = 0, gSum = 0, gSq = 0, aMax = 0;
    for (uint16_t i = 0; i < _ringCount; i++) {
      aSum += _magRing[i]; aSq += _magRing[i] * _magRing[i];
      gSum += _gyroRing[i]; gSq += _gyroRing[i] * _gyroRing[i];
      if (_magRing[i] > aMax) aMax = _magRing[i];
    }
    if (_ringCount > 1) {
      const float n = (float)_ringCount;
      float av = aSq / n - (aSum / n) * (aSum / n);
      float gv = gSq / n - (gSum / n) * (gSum / n);
      t.accelVar = av > 0 ? av : 0;
      t.gyroVar  = gv > 0 ? gv : 0;
    } else { t.accelVar = t.gyroVar = 0; }
    t.impactGMax = aMax;

    // Dominant motion frequency from zero crossings of the band-passed signal
    uint16_t crossings = 0;
    if (_ringCount == kRingN && t.accelVar > 1e-4f) {
      for (uint16_t k = 1; k < kRingN; k++) {
        const float a = _dynRing[(_ringIdx + k - 1) % kRingN];
        const float b = _dynRing[(_ringIdx + k) % kRingN];
        if ((a < 0 && b >= 0) || (a > 0 && b <= 0)) crossings++;
      }
      t.motionFreqHz = crossings / 2.0f / (MOTION_VAR_WINDOW_MS / 1000.0f);
    } else t.motionFreqHz = 0;

    // Steps
    rollBins(nowMs);
    t.stepsWindow = _binsSum;
    t.stepsTotal  = _stepsTotal;
    uint16_t recent = 0;                                   // steps in the last 15 s → cadence
    for (uint8_t k = 0; k < 15; k++) recent += _bins[(_binIdx + kBinN - k) % kBinN];
    t.cadenceSpm = recent * 4.0f;

    // Coarse on-device activity label (same vocabulary as the training data)
    if (!_present)                                              t.edgeActivity = "Unknown";
    else if (t.cadenceSpm >= 130 && t.accelVar > 0.05f)          t.edgeActivity = "Running";
    else if (t.cadenceSpm >= 30)                                 t.edgeActivity = "Walking";
    else if (t.accelVar > 0.02f)                                 t.edgeActivity = "Exercising";
    else if (t.accelVar < 0.0004f && t.hrValid && t.heartRate < 60) t.edgeActivity = "Sleeping";
    else                                                         t.edgeActivity = "Resting";
  }

private:
  TwoWire* _wire = nullptr;
  uint8_t  _addr = I2C_ADDR_MPU6050, _whoAmI = 0;
  bool     _present = false, _init = false;
  uint32_t _readErrors = 0;

  float _ax = 0, _ay = 0, _az = 1, _gx = 0, _gy = 0, _gz = 0, _accelMag = 1;
  float _gravX = 0, _gravY = 0, _gravZ = 1, _magLp = 1, _dyn = 0;

  float    _magRing[kRingN] = {0}, _gyroRing[kRingN] = {0}, _dynRing[kRingN] = {0};
  uint16_t _ringIdx = 0, _ringCount = 0;

  float    _orientHist[kOrientN][3] = {{0}};
  uint8_t  _orientIdx = 0;
  uint32_t _lastOrientMs = 0;

  // Pedometer
  bool     _stepArmed = true;
  uint32_t _lastStepMs = 0, _stepsTotal = 0;
  uint8_t  _pendingSteps = 0;
  uint8_t  _bins[kBinN] = {0};
  uint8_t  _binIdx = 0;
  uint16_t _binsSum = 0;
  uint32_t _binSec = 0;

  // Fall detector
  enum FallStage : uint8_t { F_IDLE, F_SETTLE, F_WATCH };
  FallStage _fstage = F_IDLE;
  uint32_t  _lastFreefallMs = 0, _impactMs = 0, _watchStartMs = 0, _fallHoldoffUntil = 0;
  float     _impactG = 0, _preOrient[3] = {0, 0, 1};
  bool      _freefall = false;
  uint16_t  _watchSamples = 0, _watchMoving = 0;
  FallEvent _fall = { false, 0, 0, false, "low" };

  // ── I2C helpers ──
  bool writeReg(uint8_t reg, uint8_t val) {
    _wire->beginTransmission(_addr);
    _wire->write(reg);
    _wire->write(val);
    return _wire->endTransmission() == 0;
  }
  bool readRegs(uint8_t reg, uint8_t* buf, uint8_t n) {
    _wire->beginTransmission(_addr);
    _wire->write(reg);
    if (_wire->endTransmission(false) != 0) return false;
    if (_wire->requestFrom((uint8_t)_addr, (uint8_t)n) != n) return false;
    for (uint8_t i = 0; i < n; i++) buf[i] = (uint8_t)_wire->read();
    return true;
  }

  // ── Pedometer ──
  void detectStep(uint32_t nowMs) {
    if (!_stepArmed) {                                   // wait for the signal to fall back before the next peak
      if (_dyn < STEP_PEAK_THRESHOLD_G * 0.5f) _stepArmed = true;
      return;
    }
    if (_dyn <= STEP_PEAK_THRESHOLD_G) return;
    _stepArmed = false;
    if (nowMs - _lastStepMs < STEP_MIN_INTERVAL_MS) return;      // too fast to be a step
    if (nowMs - _lastStepMs > STEP_BOUT_GAP_MS) _pendingSteps = 0; // new walking bout
    _lastStepMs = nowMs;
    if (_pendingSteps < STEP_BOUT_MIN_STEPS) {
      _pendingSteps++;
      if (_pendingSteps == STEP_BOUT_MIN_STEPS)          // rhythm confirmed → count the buffered steps
        for (uint8_t i = 0; i < STEP_BOUT_MIN_STEPS; i++) addStep(nowMs);
    } else {
      addStep(nowMs);
    }
  }
  void addStep(uint32_t nowMs) {
    _stepsTotal++;
    rollBins(nowMs);
    if (_bins[_binIdx] < 255) { _bins[_binIdx]++; _binsSum++; }
  }
  void rollBins(uint32_t nowMs) {                        // advance the one-second bins to "now"
    const uint32_t sec = nowMs / 1000;
    if (sec == _binSec) return;
    uint32_t advance = sec - _binSec;
    if (advance > kBinN) advance = kBinN;
    while (advance--) {
      _binIdx = (_binIdx + 1) % kBinN;
      _binsSum -= _bins[_binIdx];
      _bins[_binIdx] = 0;
    }
    _binSec = sec;
  }

  // ── Fall detection ──
  static float angleBetweenDeg(const float* a, const float* b) {
    const float na = sqrtf(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]);
    const float nb = sqrtf(b[0]*b[0] + b[1]*b[1] + b[2]*b[2]);
    if (na < 1e-3f || nb < 1e-3f) return 0;
    float c = (a[0]*b[0] + a[1]*b[1] + a[2]*b[2]) / (na * nb);
    if (c > 1) c = 1;
    if (c < -1) c = -1;
    return acosf(c) * 57.2957795f;
  }

  void updateFallFsm(uint32_t nowMs, float mag, float gmag) {
    if (mag < FALL_FREEFALL_G) _lastFreefallMs = nowMs;

    switch (_fstage) {
      case F_IDLE:
        if (mag > FALL_IMPACT_G && (int32_t)(nowMs - _fallHoldoffUntil) >= 0) {
          _impactMs = nowMs;
          _impactG  = mag;
          _freefall = _lastFreefallMs != 0 && (nowMs - _lastFreefallMs) < 1000;
          const uint8_t oldest = _orientIdx;               // ≈2 s before the impact
          _preOrient[0] = _orientHist[oldest][0]; _preOrient[1] = _orientHist[oldest][1]; _preOrient[2] = _orientHist[oldest][2];
          _fstage = F_SETTLE;
        }
        break;

      case F_SETTLE:                                       // the tumble itself — just track the peak
        if (mag > _impactG) _impactG = mag;
        if (nowMs - _impactMs >= FALL_SETTLE_MS) {
          _fstage = F_WATCH; _watchStartMs = nowMs; _watchSamples = 0; _watchMoving = 0;
        }
        break;

      case F_WATCH:                                        // is the wearer moving afterwards?
        _watchSamples++;
        if (fabsf(mag - 1.0f) > FALL_IMMOBILE_ACCEL_G || gmag > FALL_IMMOBILE_GYRO_RADS) _watchMoving++;
        if (nowMs - _watchStartMs >= FALL_IMMOBILE_WINDOW_MS) {
          const bool  immobile = _watchMoving <= (uint16_t)(FALL_IMMOBILE_MAX_RATIO * _watchSamples);
          const float postOrient[3] = { _gravX, _gravY, _gravZ };
          const float orient = angleBetweenDeg(_preOrient, postOrient);
          if (immobile) {
            const bool posture = orient >= FALL_ORIENT_CHANGE_DEG;
            const bool hardHit = _impactG >= 4.0f;
            _fall.pending    = true;
            _fall.impactG    = _impactG;
            _fall.orientDeg  = orient;
            _fall.freefall   = _freefall;
            _fall.confidence = (hardHit && (posture || _freefall)) ? "high"
                             : (hardHit || posture || _freefall)   ? "medium" : "low";
            _fallHoldoffUntil = nowMs + FALL_RETRIGGER_HOLDOFF_MS;
          }
          _fstage = F_IDLE;
        }
        break;
    }
  }
};

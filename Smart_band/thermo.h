/**
 * NeuroLink Wear — skin temperature module (MLX90614, raw SMBus)
 * ---------------------------------------------------------------
 *  Reads object (skin) and ambient temperature once per second, verifies the
 *  SMBus PEC (CRC-8) of every transfer, and derives a core-temperature
 *  estimate (skin + calibrated offset) because the model was trained on
 *  core-range values. The bus is dropped to 100 kHz only while talking to
 *  the MLX90614 — the other devices keep running at 400 kHz.
 */
#pragma once

#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "shared_state.h"

class ThermoSensor {
public:
  bool begin(TwoWire& wire) {
    _wire = &wire;
    float t;
    _present = readTemp(0x06, t);          // ambient register — proves the device answers with a valid PEC
    if (!_present) { delay(50); _present = readTemp(0x06, t); }   // one retry (sensor wakes slowly)
    return _present;
  }

  void service(uint32_t nowMs) {
    if (!_present || nowMs - _lastMs < THERMO_SAMPLE_MS) return;
    _lastMs = nowMs;
    float obj, amb;
    if (readTemp(0x07, obj)) {                          // Tobj1 = skin under the sensor
      _skin = _haveSkin ? _skin + (obj - _skin) * 0.3f : obj;
      _haveSkin = true; _lastGoodMs = nowMs;
    } else _errors++;
    if (readTemp(0x06, amb)) {                          // Ta = sensor die / ambient
      _amb = _haveAmb ? _amb + (amb - _amb) * 0.3f : amb;
      _haveAmb = true;
    }
  }

  bool  present() const  { return _present; }
  float skinC() const    { return _skin; }
  float ambientC() const { return _amb; }
  uint32_t errors() const { return _errors; }

  void fill(Telemetry& t, uint32_t nowMs) const {
    t.thermoPresent = _present;
    t.skinTempC     = _skin;
    t.ambientTempC  = _amb;
    t.tempValid = _present && _haveSkin && (nowMs - _lastGoodMs) < 5000 &&
                  _skin >= TEMP_SKIN_VALID_MIN_C && _skin <= TEMP_SKIN_VALID_MAX_C;
    float body = _skin + TEMP_SKIN_TO_CORE_OFFSET_C;
    if (body < 30.0f) body = 30.0f;
    if (body > 43.0f) body = 43.0f;
    t.bodyTempC = body;
  }

  /** SMBus CRC-8 (polynomial 0x07) as used by the MLX90614 PEC byte. */
  static uint8_t crc8(const uint8_t* data, size_t len) {
    uint8_t crc = 0;
    for (size_t i = 0; i < len; i++) {
      crc ^= data[i];
      for (uint8_t b = 0; b < 8; b++) crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
    }
    return crc;
  }

private:
  TwoWire* _wire = nullptr;
  bool     _present = false, _haveSkin = false, _haveAmb = false;
  uint32_t _lastMs = 0, _lastGoodMs = 0, _errors = 0;
  float    _skin = 0, _amb = 0;

  bool readTemp(uint8_t reg, float& outC) {
    _wire->setClock(MLX_I2C_CLOCK_HZ);
    _wire->beginTransmission(I2C_ADDR_MLX90614);
    _wire->write(reg);
    bool ok = _wire->endTransmission(false) == 0 &&
              _wire->requestFrom((uint8_t)I2C_ADDR_MLX90614, (uint8_t)3) == 3;
    uint8_t lsb = 0, msb = 0, pec = 0;
    if (ok) { lsb = (uint8_t)_wire->read(); msb = (uint8_t)_wire->read(); pec = (uint8_t)_wire->read(); }
    _wire->setClock(I2C_CLOCK_HZ);
    if (!ok) return false;

    const uint8_t frame[5] = { (uint8_t)(I2C_ADDR_MLX90614 << 1), reg, (uint8_t)((I2C_ADDR_MLX90614 << 1) | 1), lsb, msb };
    if (crc8(frame, 5) != pec) return false;             // corrupted transfer
    const uint16_t raw = ((uint16_t)msb << 8) | lsb;
    if (raw & 0x8000) return false;                      // sensor error flag
    outC = raw * 0.02f - 273.15f;
    return outC > -40.0f && outC < 125.0f;
  }
};

/**
 * NeuroLink Wear — GPS module (u-blox NEO-6M over UART2, TinyGPSPlus)
 * --------------------------------------------------------------------
 *  Serviced from the network task (the GPS is a UART device, so it does not
 *  compete with the I2C sensors). Provides the fix used in emergency packets
 *  and a UTC time fallback for TLS when NTP is unreachable.
 */
#pragma once

#include <Arduino.h>
#include <time.h>
#include <TinyGPS++.h>
#include "config.h"
#include "shared_state.h"

class GpsModule {
public:
  void begin() {
    Serial2.begin(9600, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
    _enabled = true;
  }

  void service() {
    if (!_enabled) return;
    while (Serial2.available()) _gps.encode((char)Serial2.read());
  }

  bool present() const { return _enabled && _gps.charsProcessed() > 20; }        // NMEA stream seen
  bool healthy() const { return present() && _gps.passedChecksum() > 0; }
  bool fix() const     { return _gps.location.isValid() && _gps.location.age() < 15000; }

  /** UTC epoch from the GPS date/time (valid even before a position fix). */
  bool epochUtc(time_t& out) {
    if (!_gps.date.isValid() || !_gps.time.isValid() || _gps.date.age() > 5000) return false;
    const int y = _gps.date.year();
    if (y < 2024) return false;                                  // default date before first fix
    const int64_t days = daysFromCivil(y, _gps.date.month(), _gps.date.day());
    out = (time_t)(days * 86400 + _gps.time.hour() * 3600L + _gps.time.minute() * 60L + _gps.time.second());
    return true;
  }

  void fill(LinkStatus& l) {
    l.gpsPresent = present();
    l.gpsFix     = fix();
    l.lat  = l.gpsFix ? _gps.location.lat() : 0.0;
    l.lon  = l.gpsFix ? _gps.location.lng() : 0.0;
    l.sats = _gps.satellites.isValid() ? (uint8_t)_gps.satellites.value() : 0;
    l.hdop = _gps.hdop.isValid() ? (float)_gps.hdop.hdop() : 0.0f;
    l.altM = _gps.altitude.isValid() ? (float)_gps.altitude.meters() : 0.0f;
    l.speedKmh = _gps.speed.isValid() ? (float)_gps.speed.kmph() : 0.0f;
    l.gpsAgeMs = _gps.location.isValid() ? _gps.location.age() : 0xFFFFFFFFUL;
  }

private:
  TinyGPSPlus _gps;
  bool _enabled = false;

  // Howard Hinnant's days-from-civil (proleptic Gregorian) → days since 1970-01-01
  static int64_t daysFromCivil(int y, unsigned m, unsigned d) {
    y -= m <= 2;
    const int era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = (unsigned)(y - era * 400);
    const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return (int64_t)era * 146097 + (int64_t)doe - 719468;
  }
};

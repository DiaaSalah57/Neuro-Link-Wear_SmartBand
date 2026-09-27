/**
 * NeuroLink Wear — OLED UI (SSD1306 128×64, U8g2 page-buffer mode)
 * ------------------------------------------------------------------
 *  Page-buffer mode sends the frame in 8 small chunks; the PPG FIFO is drained
 *  between chunks so the heart-beat sampling never stalls while drawing.
 *
 *  Screens (priority order):
 *    1. safety prompt / escalated / resolved
 *    2. backend alert overlay (auto-dismisses after its TTL)
 *    3. user pages, cycled with a short button press:
 *         VITALS → NETWORK → GPS
 */
#pragma once

#include <Arduino.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <U8g2lib.h>
#include "config.h"
#include "shared_state.h"
#include "gsr.h"

class Display {
public:
  enum Page : uint8_t { PAGE_VITALS = 0, PAGE_NETWORK, PAGE_GPS, PAGE_COUNT };
  typedef void (*BetweenPagesFn)();

  Display() : _u8g2(U8G2_R0, U8X8_PIN_NONE, PIN_I2C_SCL, PIN_I2C_SDA) {}

  void begin(bool detected) {
    _present = detected;
    if (!_present) return;
    _u8g2.setBusClock(I2C_CLOCK_HZ);
    _u8g2.begin();
    _u8g2.setFontMode(1);                // transparent fonts
    _u8g2.setFontPosBaseline();
  }

  bool present() const { return _present; }
  void nextPage() { _page = (Page)((_page + 1) % PAGE_COUNT); }
  Page page() const { return _page; }

  /** Boot screen: title + up to two status lines. */
  void showBoot(const char* line1, const char* line2) {
    if (!_present) return;
    _u8g2.firstPage();
    do {
      _u8g2.setFont(u8g2_font_helvB12_tf);
      centered(20, "NeuroLink Wear");
      _u8g2.setFont(u8g2_font_5x7_tf);
      char fw[40];
      snprintf(fw, sizeof fw, "fw %s  %s", FIRMWARE_VERSION, g_deviceId);
      centered(31, fw);
      _u8g2.setFont(u8g2_font_6x10_tf);
      centered(47, line1);
      centered(60, line2);
    } while (_u8g2.nextPage());
  }

  void render(const Telemetry& t, const LinkStatus& l, const AlertState& a,
              uint32_t nowMs, bool beatFlash, BetweenPagesFn betweenPages) {
    if (!_present) return;
    _u8g2.firstPage();
    do {
      drawFrame(t, l, a, nowMs, beatFlash);
      if (betweenPages) betweenPages();
    } while (_u8g2.nextPage());
  }

private:
  U8G2_SSD1306_128X64_NONAME_1_HW_I2C _u8g2;
  bool _present = false;
  Page _page = PAGE_VITALS;

  // 24×21 heart (from the original sketch)
  static const unsigned char* heartBitmap() {
    static const unsigned char bmp[] U8X8_PROGMEM = {
      0xC0, 0x03, 0x0F, 0x60, 0x8E, 0x31, 0x30, 0xD8, 0x60, 0x18, 0x70, 0x40, 0x08, 0x30, 0xC0, 0x08,
      0x20, 0x80, 0x08, 0x20, 0x80, 0x08, 0x02, 0x80, 0x08, 0x02, 0x80, 0x08, 0x03, 0xC0, 0x10, 0x11,
      0x40, 0x10, 0x1D, 0x20, 0xFF, 0xEC, 0x10, 0x80, 0x0C, 0x18, 0x80, 0x09, 0x0C, 0x00, 0x03, 0x06,
      0x00, 0x06, 0x03, 0x00, 0x8C, 0x01, 0x00, 0xD8, 0x00, 0x00, 0x70, 0x00, 0x00, 0x20, 0x00
    };
    return bmp;
  }

  void centered(uint8_t y, const char* s) {
    const int w = _u8g2.getStrWidth(s);
    int x = (128 - w) / 2; if (x < 0) x = 0;
    _u8g2.drawStr((u8g2_uint_t)x, y, s);
  }

  // ── Frame dispatcher ──
  void drawFrame(const Telemetry& t, const LinkStatus& l, const AlertState& a, uint32_t nowMs, bool beatFlash) {
    switch (t.safety) {
      case SAFETY_PROMPT:    drawPrompt(t, nowMs);   return;
      case SAFETY_ESCALATED: drawEscalated(l, nowMs); return;
      case SAFETY_RESOLVED:  drawResolved();         return;
      default: break;
    }
    drawStatusBar(t, l, nowMs);
    const bool alertActive = a.id != 0 && !a.requireAck && (nowMs - a.receivedMs) < a.ttlMs;
    if (alertActive) { drawAlert(a, nowMs); return; }
    switch (_page) {
      case PAGE_NETWORK: drawNetwork(l, nowMs); break;
      case PAGE_GPS:     drawGps(l); break;
      default:           drawVitals(t, beatFlash); break;
    }
  }

  // ── Status bar (y 0–9) ──
  void drawStatusBar(const Telemetry& t, const LinkStatus& l, uint32_t nowMs) {
    _u8g2.setFont(u8g2_font_5x7_tf);
    // left: page name
    _u8g2.drawStr(0, 7, _page == PAGE_VITALS ? "LIVE" : _page == PAGE_NETWORK ? "NET" : "GPS");
    // centre: clock (if synced) else uptime
    char buf[12];
    if (l.timeSynced) {
      time_t now = time(nullptr); struct tm tmv; localtime_r(&now, &tmv);
      snprintf(buf, sizeof buf, "%02d:%02d", tmv.tm_hour, tmv.tm_min);
    } else {
      const uint32_t s = nowMs / 1000;
      snprintf(buf, sizeof buf, "up %lum", (unsigned long)(s / 60));
    }
    centered(7, buf);
    // right: Wi-Fi bars · MQTT dot · GPS sats
    const int bars = !l.wifiConnected ? 0 : l.rssi > -60 ? 4 : l.rssi > -70 ? 3 : l.rssi > -80 ? 2 : 1;
    for (int i = 0; i < 4; i++) {
      const int h = 2 + i * 2, x = 86 + i * 3;
      if (i < bars) _u8g2.drawBox(x, 8 - h, 2, h); else _u8g2.drawHLine(x, 7, 2);
    }
    if (l.mqttConnected) _u8g2.drawDisc(103, 4, 2); else _u8g2.drawCircle(103, 4, 2);
    if (l.gpsFix)        snprintf(buf, sizeof buf, "G%u", (unsigned)l.sats);
    else if (l.gpsPresent) snprintf(buf, sizeof buf, "G-");
    else                 snprintf(buf, sizeof buf, "Gx");
    _u8g2.drawStr(110, 7, buf);
    _u8g2.drawHLine(0, 9, 128);
    (void)t;
  }

  // ── Page: live vitals ──
  void drawVitals(const Telemetry& t, bool beatFlash) {
    char buf[24];
    // Heart (frame flashes on every detected beat) + BPM
    _u8g2.drawXBMP(2, 13, 24, 21, heartBitmap());
    if (beatFlash) _u8g2.drawRFrame(0, 11, 28, 25, 3);
    if (!t.ppgPresent) {
      _u8g2.setFont(u8g2_font_6x10_tf);
      _u8g2.drawStr(30, 24, "no PPG");
      _u8g2.drawStr(30, 34, "sensor");
    } else if (!t.ppgContact) {
      _u8g2.setFont(u8g2_font_6x10_tf);
      _u8g2.drawStr(30, 24, "Wear band");
      _u8g2.drawStr(30, 34, "snugly");
    } else if (!t.hrValid) {
      _u8g2.setFont(u8g2_font_6x10_tf);
      _u8g2.drawStr(30, 24, "reading");
      _u8g2.drawStr(30, 34, "pulse...");
    } else {
      _u8g2.setFont(u8g2_font_logisoso20_tn);
      snprintf(buf, sizeof buf, "%d", (int)(t.heartRate + 0.5f));
      _u8g2.drawStr(30, 34, buf);
      _u8g2.setFont(u8g2_font_5x7_tf);
      _u8g2.drawStr(32, 45, "bpm");
    }
    // Right column
    _u8g2.setFont(u8g2_font_6x10_tf);
    if (t.spo2Valid) snprintf(buf, sizeof buf, "SpO2 %d%%", (int)(t.spo2 + 0.5f));
    else             snprintf(buf, sizeof buf, "SpO2 --");
    _u8g2.drawStr(80, 21, buf);
    if (t.tempValid) snprintf(buf, sizeof buf, "%.1f%cC", t.bodyTempC, 0xB0);
    else             snprintf(buf, sizeof buf, "Temp --");
    _u8g2.drawStr(80, 33, buf);
    snprintf(buf, sizeof buf, "Str %s", t.gsrPresent ? GsrSensor::stressLabel(t.stressScore) : "--");
    _u8g2.drawStr(80, 45, buf);
    // Bottom row
    _u8g2.drawHLine(0, 51, 128);
    if (t.hrv > 0) snprintf(buf, sizeof buf, "HRV %dms", (int)(t.hrv + 0.5f));
    else           snprintf(buf, sizeof buf, "HRV --");
    _u8g2.drawStr(2, 62, buf);
    if (t.imuPresent) snprintf(buf, sizeof buf, "%s %u", t.edgeActivity, (unsigned)t.stepsWindow);
    else              snprintf(buf, sizeof buf, "no IMU");
    _u8g2.drawStr(60, 62, buf);
  }

  // ── Page: network ──
  void drawNetwork(const LinkStatus& l, uint32_t nowMs) {
    char buf[32];
    _u8g2.setFont(u8g2_font_6x10_tf);
    if (l.wifiConnected) snprintf(buf, sizeof buf, "WiFi %ddBm", (int)l.rssi); else snprintf(buf, sizeof buf, "WiFi: connecting");
    _u8g2.drawStr(0, 20, buf);
    snprintf(buf, sizeof buf, "IP %s", l.wifiConnected ? l.ip : "-");
    _u8g2.drawStr(0, 31, buf);
    if (l.mqttConnected) snprintf(buf, sizeof buf, "MQTT ok  #%lu", (unsigned long)l.seq);
    else                 snprintf(buf, sizeof buf, "MQTT down (rc %d)", l.mqttState);
    _u8g2.drawStr(0, 42, buf);
    const uint32_t age = l.lastPublishMs ? (nowMs - l.lastPublishMs) / 1000 : 0;
    snprintf(buf, sizeof buf, "pub %lus ago  fail %lu", (unsigned long)age, (unsigned long)l.publishFailures);
    _u8g2.drawStr(0, 53, buf);
    snprintf(buf, sizeof buf, "time %s  %s", l.timeSynced ? l.timeSource : "--", g_deviceId);
    _u8g2.drawStr(0, 63, buf);
  }

  // ── Page: GPS ──
  void drawGps(const LinkStatus& l) {
    char buf[32];
    _u8g2.setFont(u8g2_font_6x10_tf);
    if (!l.gpsPresent)      snprintf(buf, sizeof buf, "GPS: no module");
    else if (!l.gpsFix)     snprintf(buf, sizeof buf, "GPS: searching %u", (unsigned)l.sats);
    else                    snprintf(buf, sizeof buf, "GPS fix  %u sats", (unsigned)l.sats);
    _u8g2.drawStr(0, 20, buf);
    if (l.gpsFix) {
      snprintf(buf, sizeof buf, "Lat %.5f", l.lat); _u8g2.drawStr(0, 32, buf);
      snprintf(buf, sizeof buf, "Lon %.5f", l.lon); _u8g2.drawStr(0, 43, buf);
      snprintf(buf, sizeof buf, "Alt %dm  HDOP %.1f", (int)l.altM, l.hdop); _u8g2.drawStr(0, 54, buf);
      snprintf(buf, sizeof buf, "age %lus  %.1fkm/h", (unsigned long)(l.gpsAgeMs / 1000), l.speedKmh); _u8g2.drawStr(0, 64, buf);
    } else {
      _u8g2.drawStr(0, 36, "Move near a window");
      _u8g2.drawStr(0, 48, "for a first fix.");
    }
  }

  // ── Backend alert overlay ──
  void drawAlert(const AlertState& a, uint32_t nowMs) {
    // inverted banner
    _u8g2.drawBox(0, 11, 128, 13);
    _u8g2.setDrawColor(0);
    _u8g2.setFont(u8g2_font_6x10_tf);
    char buf[32];
    snprintf(buf, sizeof buf, "! %s", a.condition);
    _u8g2.drawStr(2, 21, buf);
    const int sw = _u8g2.getStrWidth(a.severity);
    _u8g2.drawStr(126 - sw, 21, a.severity);
    _u8g2.setDrawColor(1);
    // message, wrapped onto two lines of 21 characters
    char line[22];
    const size_t len = strlen(a.message);
    for (int i = 0; i < 2; i++) {
      const size_t off = i * 21;
      if (off >= len) break;
      strcopy(line, sizeof line, a.message + off);
      _u8g2.drawStr(0, 37 + i * 11, line);
    }
    if (len == 0) _u8g2.drawStr(0, 37, a.ensemble[0] ? a.ensemble : "See dashboard");
    _u8g2.setFont(u8g2_font_5x7_tf);
    const uint32_t left = (a.ttlMs - (nowMs - a.receivedMs)) / 1000;
    snprintf(buf, sizeof buf, "dismisses in %lus", (unsigned long)left);
    _u8g2.drawStr(0, 63, buf);
  }

  // ── Safety screens ──
  void drawPrompt(const Telemetry& t, uint32_t nowMs) {
    const bool blink = (nowMs / 500) & 1;
    if (blink) _u8g2.drawFrame(0, 0, 128, 64);
    _u8g2.setFont(u8g2_font_helvB12_tf);
    const bool isFall = strncmp(t.safetyReason, "FALL", 4) == 0;
    centered(15, isFall ? "FALL DETECTED" : "HEALTH ALERT");
    _u8g2.setFont(u8g2_font_6x10_tf);
    if (!isFall) {                                  // show the backend condition
      const char* cond = strchr(t.safetyReason, ':');
      centered(27, cond ? cond + 1 : t.safetyReason);
    } else centered(27, "Are you OK?");
    int32_t leftMs = (int32_t)(t.promptDeadlineMs - nowMs);
    if (leftMs < 0) leftMs = 0;
    char buf[16];
    snprintf(buf, sizeof buf, "%ld", (long)((leftMs + 999) / 1000));
    _u8g2.setFont(u8g2_font_logisoso20_tn);
    centered(50, buf);
    const int w = (int)(128L * leftMs / ((int32_t)ACK_WINDOW_S * 1000L));
    _u8g2.drawBox(0, 53, (u8g2_uint_t)w, 2);
    _u8g2.setFont(u8g2_font_5x7_tf);
    centered(63, "PRESS BUTTON if you are OK");
  }

  void drawEscalated(const LinkStatus& l, uint32_t nowMs) {
    const bool blink = (nowMs / 700) & 1;
    if (blink) { _u8g2.drawBox(0, 0, 128, 18); _u8g2.setDrawColor(0); }
    _u8g2.setFont(u8g2_font_helvB12_tf);
    centered(14, "HELP REQUESTED");
    _u8g2.setDrawColor(1);
    _u8g2.setFont(u8g2_font_6x10_tf);
    centered(30, l.mqttConnected ? "Caregivers notified" : "Sending... (offline)");
    char buf[32];
    if (l.gpsFix) snprintf(buf, sizeof buf, "GPS fix sent (%u sats)", (unsigned)l.sats);
    else          snprintf(buf, sizeof buf, "GPS: no fix yet");
    centered(42, buf);
    _u8g2.setFont(u8g2_font_5x7_tf);
    centered(54, "Stay calm. Help is coming.");
    centered(63, "press = I'm OK   hold = resend");
  }

  void drawResolved() {
    _u8g2.setFont(u8g2_font_helvB12_tf);
    centered(28, "Glad you're OK");
    _u8g2.setFont(u8g2_font_6x10_tf);
    centered(46, "Alert cancelled");
  }
};

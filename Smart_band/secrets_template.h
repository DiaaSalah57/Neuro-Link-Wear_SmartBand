/**
 * NeuroLink Wear — credentials TEMPLATE
 * -------------------------------------
 *   1. Copy this file to  secrets.h  (same folder).
 *   2. Fill in your Wi-Fi network and HiveMQ Cloud cluster details.
 *   3. secrets.h is git-ignored, so your credentials never reach the repo.
 *
 * If secrets.h is missing the sketch still compiles using these placeholders
 * (with a compiler warning) so you can test the sensors offline.
 */
#pragma once

// ─── Wi-Fi (2.4 GHz only — the ESP32 has no 5 GHz radio) ───
#define WIFI_SSID          "YOUR_WIFI_SSID"
#define WIFI_PASSWORD      "YOUR_WIFI_PASSWORD"

// ─── HiveMQ Cloud  (Console → your cluster → "Overview" for the URL,
//                    "Access Management" to create the username/password) ───
#define MQTT_HOST          "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.s1.eu.hivemq.cloud"
#define MQTT_PORT          8883
#define MQTT_USERNAME      "neurolink-band"
#define MQTT_PASSWORD      "YOUR_HIVEMQ_PASSWORD"

// ─── Optional: fixed, human-friendly device id (comment out to derive from MAC) ───
// #define DEVICE_ID_OVERRIDE "nlw-001"

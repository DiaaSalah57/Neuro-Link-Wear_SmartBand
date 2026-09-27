/*
  =====================================================
   NeuroLink Wear - GPS NEO-6M Test Sketch (ESP32)
  =====================================================

  Purpose:
    Standalone test for the u-blox NEO-6M GPS module
    before integrating it into the main smart band code.

  Library required (Arduino Library Manager):
    - TinyGPSPlus  by Mikal Hart

  Wiring (ESP32 DevKit  <-->  NEO-6M):
    NEO-6M VCC  ->  5V   (module has a 3.3V regulator;
                          use 3V3 if your board is 3.3V only)
    NEO-6M GND  ->  GND
    NEO-6M TX   ->  ESP32 GPIO16  (RX2)   <-- data in
    NEO-6M RX   ->  ESP32 GPIO17  (TX2)   <-- optional

    NOTE: GPS TX is 3.3V logic, so no level shifter is needed.
          Keep the antenna outdoors / near a window.
          First fix (cold start) can take 30 s - 2 min.

  What it does:
    1. Reads NMEA sentences on UART2 at 9600 baud.
    2. Parses them with TinyGPS++.
    3. Prints latitude, longitude, altitude, speed,
       satellites, HDOP and UTC date/time every second.
    4. Warns you if no bytes arrive (wiring problem) or
       if bytes arrive but there is no fix yet.

  Set RAW_MODE to true to just dump raw NMEA text
  (useful to prove the module is alive).
  =====================================================
*/

#include <TinyGPSPlus.h>
#include <HardwareSerial.h>

// =====================================================
//                   CONFIGURATION
// =====================================================

#define GPS_RX_PIN   16      // ESP32 pin connected to GPS TX
#define GPS_TX_PIN   17      // ESP32 pin connected to GPS RX
#define GPS_BAUD     9600    // NEO-6M default baud rate

#define RAW_MODE     false   // true = print raw NMEA only

// UART2 of the ESP32
HardwareSerial gpsSerial(2);

// TinyGPS++ parser
TinyGPSPlus gps;

// ---------------------------------------------------
// Extra NMEA fields TinyGPS++ does not expose itself.
// These tell you what is happening WHILE searching,
// before there is any fix at all.
// ---------------------------------------------------

// $GPGSV field 3 = total satellites in view
TinyGPSCustom satsInView(gps, "GPGSV", 3);

// $GPGSV field 7 = SNR (C/N0) of the first satellite listed
TinyGPSCustom snrFirstSat(gps, "GPGSV", 7);

// $GPGSA field 2 = fix mode: 1 = none, 2 = 2D, 3 = 3D
TinyGPSCustom fixMode(gps, "GPGSA", 2);

// $GPGGA field 6 = fix quality: 0 = invalid, 1 = GPS fix
TinyGPSCustom fixQuality(gps, "GPGGA", 6);

// Timers
unsigned long lastPrint  = 0;
unsigned long lastCharIn = 0;

const unsigned long PRINT_INTERVAL = 1000;   // ms
const unsigned long NO_DATA_TIMEOUT = 5000;  // ms


// =====================================================
//                       SETUP
// =====================================================

void setup() {

  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("=====================================");
  Serial.println("   GPS NEO-6M Test  -  NeuroLink Wear");
  Serial.println("=====================================");
  Serial.print("TinyGPS++ version: ");
  Serial.println(TinyGPSPlus::libraryVersion());
  Serial.printf("UART2  RX=GPIO%d  TX=GPIO%d  @ %d baud\n",
                GPS_RX_PIN, GPS_TX_PIN, GPS_BAUD);
  Serial.println("Waiting for satellites (go outside)...");
  Serial.println();

  // Start the GPS serial port
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  lastCharIn = millis();
}


// =====================================================
//                        LOOP
// =====================================================

void loop() {

  // ---------------------------------------------------
  // 1) Feed every incoming byte to the parser
  // ---------------------------------------------------

  while (gpsSerial.available() > 0) {

    char c = gpsSerial.read();

    lastCharIn = millis();

    if (RAW_MODE) {
      Serial.write(c);          // dump raw NMEA
    } else {
      gps.encode(c);            // parse
    }
  }

  if (RAW_MODE) {
    return;
  }

  // ---------------------------------------------------
  // 2) Print a report once per second
  // ---------------------------------------------------

  if (millis() - lastPrint >= PRINT_INTERVAL) {

    lastPrint = millis();

    // No bytes at all -> wiring / baud rate problem
    if (millis() - lastCharIn > NO_DATA_TIMEOUT) {

      Serial.println("[ERROR] No data from GPS module!");
      Serial.println("        Check: GPS TX -> ESP32 GPIO16,");
      Serial.println("               common GND, VCC 5V/3V3,");
      Serial.println("               baud rate 9600.");
      Serial.println();
      return;
    }

    printGpsReport();
  }
}


// =====================================================
//                    REPORT PRINTER
// =====================================================

void printGpsReport() {

  Serial.println("------------- GPS STATUS -------------");

  // ---------------- Search progress -----------------
  // Shown even when there is no fix, so you can tell
  // "acquiring" apart from "antenna dead".

  Serial.print("Searching   : ");
  Serial.print(millis() / 1000);
  Serial.println(" s since boot");

  Serial.print("Sats in view: ");
  Serial.println(satsInView.isUpdated() || satsInView.age() < 5000
                 ? satsInView.value() : "--");

  Serial.print("Best SNR    : ");
  Serial.print(snrFirstSat.age() < 5000 ? snrFirstSat.value() : "--");
  Serial.println("  (30+ = strong, under 20 = too weak to lock)");

  Serial.print("Fix mode    : ");
  if (fixMode.age() < 5000 && fixMode.value()[0]) {
    switch (fixMode.value()[0]) {
      case '1': Serial.println("1 = NO FIX (searching)"); break;
      case '2': Serial.println("2 = 2D fix");             break;
      case '3': Serial.println("3 = 3D fix");             break;
      default:  Serial.println(fixMode.value());          break;
    }
  } else {
    Serial.println("--");
  }

  Serial.print("Fix quality : ");
  Serial.println(fixQuality.age() < 5000 && fixQuality.value()[0]
                 ? fixQuality.value() : "--");

  // ------------------- Satellites -------------------
  Serial.print("Sats used   : ");
  if (gps.satellites.isValid()) {
    Serial.println(gps.satellites.value());
  } else {
    Serial.println("--");
  }

  // ---------------------- HDOP ----------------------
  Serial.print("HDOP       : ");
  if (gps.hdop.isValid()) {
    Serial.println(gps.hdop.hdop(), 2);
  } else {
    Serial.println("--");
  }

  // -------------------- Location --------------------
  if (gps.location.isValid()) {

    Serial.print("Latitude   : ");
    Serial.println(gps.location.lat(), 6);

    Serial.print("Longitude  : ");
    Serial.println(gps.location.lng(), 6);

    Serial.print("Google Maps: https://maps.google.com/?q=");
    Serial.print(gps.location.lat(), 6);
    Serial.print(",");
    Serial.println(gps.location.lng(), 6);

    Serial.print("Age (ms)   : ");
    Serial.println(gps.location.age());

  } else {
    Serial.println("Latitude   : no fix yet");
    Serial.println("Longitude  : no fix yet");
  }

  // -------------------- Altitude --------------------
  Serial.print("Altitude   : ");
  if (gps.altitude.isValid()) {
    Serial.print(gps.altitude.meters(), 1);
    Serial.println(" m");
  } else {
    Serial.println("--");
  }

  // ---------------------- Speed ---------------------
  Serial.print("Speed      : ");
  if (gps.speed.isValid()) {
    Serial.print(gps.speed.kmph(), 2);
    Serial.println(" km/h");
  } else {
    Serial.println("--");
  }

  // ------------------- Date / Time ------------------
  Serial.print("UTC Date   : ");
  if (gps.date.isValid()) {
    Serial.printf("%02d/%02d/%04d\n",
                  gps.date.day(), gps.date.month(), gps.date.year());
  } else {
    Serial.println("--");
  }

  Serial.print("UTC Time   : ");
  if (gps.time.isValid()) {
    Serial.printf("%02d:%02d:%02d\n",
                  gps.time.hour(), gps.time.minute(), gps.time.second());
  } else {
    Serial.println("--");
  }

  // ------------------- Diagnostics ------------------
  Serial.print("Chars RX   : ");
  Serial.print(gps.charsProcessed());

  Serial.print(" | Sentences OK: ");
  Serial.print(gps.sentencesWithFix());

  Serial.print(" | Checksum err: ");
  Serial.println(gps.failedChecksum());

  if (gps.charsProcessed() < 10) {
    Serial.println("[WARN] Almost no valid data received.");
    Serial.println("       Check wiring / baud rate.");
  }

  Serial.println();
}

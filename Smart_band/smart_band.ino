#include <Wire.h>
#include <U8g2lib.h>
#include "MAX30105.h"
#include "heartRate.h"

// =====================================================
//                    MAX30105
// =====================================================

MAX30105 particleSensor;

const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;

long lastBeat = 0;
float beatsPerMinute;
int beatAvg = 0;


// =====================================================
//                       GSR
// =====================================================

#define GSR_PIN 34

int gsrValue = 0;
String stressLevel = "LOW";


// =====================================================
//                       OLED
// =====================================================

// 128x64 SSD1306 OLED using hardware I2C
U8G2_SSD1306_128X64_NONAME_F_HW_I2C
u8g2(U8G2_R0, U8X8_PIN_NONE);


// =====================================================
//                     HEART BITMAPS
// =====================================================

static const unsigned char beat1_bmp[] U8X8_PROGMEM = {
  0xC0, 0x03, 0x0F, 0x60, 0x8E, 0x31, 0x30, 0xD8,
  0x60, 0x18, 0x70, 0x40, 0x08, 0x30, 0xC0, 0x08,
  0x20, 0x80, 0x08, 0x20, 0x80, 0x08, 0x02, 0x80,
  0x08, 0x02, 0x80, 0x08, 0x03, 0xC0, 0x10, 0x11,
  0x40, 0x10, 0x1D, 0x20, 0xFF, 0xEC, 0x10, 0x80,
  0x0C, 0x18, 0x80, 0x09, 0x0C, 0x00, 0x03, 0x06,
  0x00, 0x06, 0x03, 0x00, 0x8C, 0x01, 0x00, 0xD8,
  0x00, 0x00, 0x70, 0x00, 0x00, 0x20, 0x00
};

static const unsigned char beat2_bmp[] U8X8_PROGMEM = {
  0x80, 0x0F, 0xF0, 0x01, 0x60, 0x38, 0x1C, 0x06,
  0x18, 0x60, 0x06, 0x18, 0x08, 0x80, 0x01, 0x10,
  0x04, 0x80, 0x01, 0x20, 0x02, 0x00, 0x00, 0x40,
  0x02, 0x00, 0x00, 0x40, 0x03, 0x10, 0x00, 0xC0,
  0x01, 0x10, 0x00, 0x80, 0x01, 0x18, 0x00, 0x80,
  0x01, 0x38, 0x00, 0x80, 0x00, 0x28, 0x00, 0x80,
  0x00, 0x28, 0x00, 0x80, 0x00, 0x28, 0x00, 0x80,
  0x00, 0x48, 0x08, 0x02, 0x00, 0x48, 0x08, 0x02,
  0x7F, 0xC4, 0xF8, 0x7E, 0xC0, 0x8C, 0x05, 0x20,
  0x80, 0x05, 0x05, 0x30, 0x00, 0x05, 0x05, 0x10,
  0x00, 0x07, 0x07, 0x08, 0x00, 0x06, 0x06, 0x04,
  0x60, 0x00, 0x02, 0x06, 0xC0, 0x00, 0x02, 0x03,
  0x80, 0x01, 0x80, 0x01, 0x00, 0xC3, 0xC0, 0x00,
  0x00, 0x66, 0x60, 0x00, 0x00, 0x3C, 0x30, 0x00,
  0x00, 0x18, 0x08, 0x00, 0x00, 0x60, 0x06, 0x00,
  0x00, 0xC0, 0x03, 0x00, 0x00, 0x80, 0x01, 0x00
};


// =====================================================
//                       SETUP
// =====================================================

void setup() {

  // Start Serial Monitor
  Serial.begin(9600);

  // Start I2C
  Wire.begin(21, 22);
  Wire.setClock(400000);

  // ---------------------------------------------------
  // OLED initialization
  // ---------------------------------------------------

  u8g2.begin();

  u8g2.clearBuffer();

  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.drawStr(10, 30, "Initializing...");

  u8g2.sendBuffer();

  // ---------------------------------------------------
  // MAX30105 initialization
  // ---------------------------------------------------

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {

    Serial.println("MAX30105 not found.");
    Serial.println("Check wiring!");

    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.drawStr(5, 25, "MAX30105 ERROR");
    u8g2.drawStr(5, 45, "Check wiring!");
    u8g2.sendBuffer();

    while (1);
  }

  Serial.println("MAX30105 detected.");
  Serial.println("Place your finger on the sensor.");

  // MAX30105 setup
  particleSensor.setup();

  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeGreen(0);

  // ---------------------------------------------------
  // GSR
  // ---------------------------------------------------

  pinMode(GSR_PIN, INPUT);

  Serial.println("GSR sensor ready.");
}


// =====================================================
//                        LOOP
// =====================================================

void loop() {

  // ===================================================
  // Read GSR
  // ===================================================

  gsrValue = analogRead(GSR_PIN);


  // ===================================================
  // Determine stress level
  // ===================================================
  //
  // These are starting thresholds only.
  // You may need to change them after calibration.
  //

  if (gsrValue < 1200) {

    stressLevel = "LOW";

  }
  else if (gsrValue < 2000) {

    stressLevel = "MED";

  }
  else {

    stressLevel = "HIGH";
  }


  // ===================================================
  // Read IR from MAX30105
  // ===================================================

  long irValue = particleSensor.getIR();


  // ===================================================
  // Check if finger is detected
  // ===================================================

  if (irValue > 50000) {

    // -----------------------------------------------
    // Detect heartbeat
    // -----------------------------------------------

    if (checkForBeat(irValue)) {

      long delta = millis() - lastBeat;

      lastBeat = millis();

      beatsPerMinute = 60 / (delta / 1000.0);


      // ---------------------------------------------
      // Check valid BPM
      // ---------------------------------------------

      if (beatsPerMinute < 255 && beatsPerMinute > 20) {

        rates[rateSpot++] = (byte)beatsPerMinute;

        rateSpot %= RATE_SIZE;


        // Calculate average BPM

        beatAvg = 0;

        for (byte x = 0; x < RATE_SIZE; x++) {

          beatAvg += rates[x];
        }

        beatAvg /= RATE_SIZE;
      }


      // =================================================
      //                    OLED DISPLAY
      // =================================================

      u8g2.clearBuffer();


      // Heart icon

      u8g2.drawXBMP(
        5,
        5,
        24,
        21,
        beat1_bmp
      );


      // BPM label

      u8g2.setFont(u8g2_font_ncenB08_tr);

      u8g2.setCursor(40, 18);
      u8g2.print("BPM");


      // BPM value

      u8g2.setFont(u8g2_font_ncenB14_tr);

      u8g2.setCursor(40, 42);
      u8g2.print(beatAvg);


      // GSR value

      u8g2.setFont(u8g2_font_ncenB08_tr);

      u8g2.setCursor(80, 18);
      u8g2.print("GSR");


      u8g2.setCursor(80, 32);
      u8g2.print(gsrValue);


      // Stress level

      u8g2.setCursor(65, 55);
      u8g2.print("Stress:");

      u8g2.setCursor(105, 55);
      u8g2.print(stressLevel);


      // Send everything to OLED

      u8g2.sendBuffer();


      // =================================================
      //                  SERIAL MONITOR
      // =================================================

      Serial.print("IR=");
      Serial.print(irValue);

      Serial.print(", BPM=");
      Serial.print(beatsPerMinute);

      Serial.print(", Avg BPM=");
      Serial.print(beatAvg);

      Serial.print(", GSR=");
      Serial.print(gsrValue);

      Serial.print(", Stress=");
      Serial.println(stressLevel);
    }
  }


  // ===================================================
  // No finger detected
  // ===================================================

  else {

    u8g2.clearBuffer();

    u8g2.setFont(u8g2_font_ncenB08_tr);

    u8g2.drawStr(25, 20, "Please place");

    u8g2.drawStr(25, 35, "your finger");

    u8g2.drawStr(25, 50, "and wait...");

    u8g2.sendBuffer();


    Serial.println("Place your index finger on the sensor.");
  }


  // Small delay

  delay(20);
}
```

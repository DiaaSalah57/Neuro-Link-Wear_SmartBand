#include <Wire.h>
#include <U8g2lib.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <TinyGPSPlus.h>
#include <Adafruit_MLX90614.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// =====================================================
// MAX30105
// =====================================================

MAX30105 particleSensor;

const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;

long lastBeat = 0;
float beatsPerMinute;
int beatAvg = 0;


// =====================================================
// GSR
// =====================================================

#define GSR_PIN 34

int gsrValue = 0;
String stressLevel = "LOW";


// =====================================================
// GPS NEO-6M
// =====================================================

#define GPS_RX_PIN 16
#define GPS_TX_PIN 17

TinyGPSPlus gps;
HardwareSerial GPS_Serial(2);

double latitude = 0.0;
double longitude = 0.0;

int satellites = 0;
bool gpsFix = false;


// =====================================================
// MLX90614
// =====================================================

Adafruit_MLX90614 mlx = Adafruit_MLX90614();

float objectTemperature = 0.0;
float ambientTemperature = 0.0;


// =====================================================
// MPU6050
// =====================================================

Adafruit_MPU6050 mpu;

float accelX = 0.0;
float accelY = 0.0;
float accelZ = 0.0;

float gyroX = 0.0;
float gyroY = 0.0;
float gyroZ = 0.0;


// =====================================================
// OLED
// =====================================================

U8G2_SSD1306_128X64_NONAME_F_HW_I2C
u8g2(U8G2_R0, U8X8_PIN_NONE);


// =====================================================
// HEART BITMAP
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


// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(9600);
  delay(500);

  Serial.println();
  Serial.println("=================================");
  Serial.println("       SMART BAND STARTING");
  Serial.println("=================================");


  // ---------------------------------------------------
  // I2C
  // ---------------------------------------------------

  Wire.begin(21, 22);
  Wire.setClock(400000);


  // ---------------------------------------------------
  // OLED
  // ---------------------------------------------------

  u8g2.begin();

  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.drawStr(10, 30, "Initializing...");
  u8g2.sendBuffer();

  delay(500);


  // ---------------------------------------------------
  // MAX30105
  // ---------------------------------------------------

  Serial.println("Initializing MAX30105...");

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {

    Serial.println("ERROR: MAX30105 not found!");

    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.drawStr(5, 25, "MAX30105 ERROR");
    u8g2.drawStr(5, 45, "Check wiring!");
    u8g2.sendBuffer();

    while (1);
  }

  Serial.println("MAX30105 OK");

  particleSensor.setup();

  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeGreen(0);


  // ---------------------------------------------------
  // GSR
  // ---------------------------------------------------

  Serial.println("Initializing GSR...");

  pinMode(GSR_PIN, INPUT);

  Serial.println("GSR OK");


  // ---------------------------------------------------
  // MLX90614
  // ---------------------------------------------------

  Serial.println("Initializing MLX90614...");

  if (!mlx.begin()) {

    Serial.println("ERROR: MLX90614 not found!");

    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.drawStr(5, 25, "MLX90614 ERROR");
    u8g2.drawStr(5, 45, "Check wiring!");
    u8g2.sendBuffer();

    while (1);
  }

  Serial.println("MLX90614 OK");


  // ---------------------------------------------------
  // MPU6050
  // ---------------------------------------------------

  Serial.println("Initializing MPU6050...");

  if (!mpu.begin(0x68, &Wire)) {

    Serial.println("ERROR: MPU6050 not found!");

    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.drawStr(5, 25, "MPU6050 ERROR");
    u8g2.drawStr(5, 45, "Check wiring!");
    u8g2.sendBuffer();

    while (1);
  }

  Serial.println("MPU6050 OK");


  // MPU6050 configuration

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);


  // ---------------------------------------------------
  // GPS
  // ---------------------------------------------------

  Serial.println("Initializing GPS...");

  GPS_Serial.begin(
    9600,
    SERIAL_8N1,
    GPS_RX_PIN,
    GPS_TX_PIN
  );

  Serial.println("GPS serial OK");

  Serial.println("Waiting for GPS fix...");
  Serial.println();

  Serial.println("=================================");
  Serial.println("       ALL SENSORS READY");
  Serial.println("=================================");

  delay(1000);
}


// =====================================================
// READ GPS
// =====================================================

void readGPS() {

  while (GPS_Serial.available()) {

    char c = GPS_Serial.read();

    gps.encode(c);
  }


  if (gps.location.isValid()) {

    gpsFix = true;

    latitude = gps.location.lat();
    longitude = gps.location.lng();

  } else {

    gpsFix = false;
  }


  if (gps.satellites.isValid()) {

    satellites = gps.satellites.value();
  }
}


// =====================================================
// READ TEMPERATURE
// =====================================================

void readTemperature() {

  objectTemperature = mlx.readObjectTempC();

  ambientTemperature = mlx.readAmbientTempC();
}


// =====================================================
// READ MPU6050
// =====================================================

void readMPU6050() {

  sensors_event_t accel;
  sensors_event_t gyro;
  sensors_event_t temp;

  mpu.getEvent(
    &accel,
    &gyro,
    &temp
  );


  accelX = accel.acceleration.x / 9.80665;
  accelY = accel.acceleration.y / 9.80665;
  accelZ = accel.acceleration.z / 9.80665;


  gyroX = gyro.gyro.x * 57.2958;
  gyroY = gyro.gyro.y * 57.2958;
  gyroZ = gyro.gyro.z * 57.2958;
}


// =====================================================
// LOOP
// =====================================================

void loop() {

  // ---------------------------------------------------
  // GPS
  // ---------------------------------------------------

  readGPS();


  // ---------------------------------------------------
  // GSR
  // ---------------------------------------------------

  gsrValue = analogRead(GSR_PIN);


  // These thresholds are only starting values.
  // They must be calibrated for your specific GSR sensor.

  if (gsrValue < 1200) {

    stressLevel = "LOW";

  } else if (gsrValue < 2000) {

    stressLevel = "MED";

  } else {

    stressLevel = "HIGH";
  }


  // ---------------------------------------------------
  // Temperature
  // ---------------------------------------------------

  readTemperature();


  // ---------------------------------------------------
  // MPU6050
  // ---------------------------------------------------

  readMPU6050();


  // ---------------------------------------------------
  // MAX30105
  // ---------------------------------------------------

  long irValue = particleSensor.getIR();


  // ===================================================
  // FINGER DETECTED
  // ===================================================

  if (irValue > 50000) {

    if (checkForBeat(irValue)) {

      long delta = millis() - lastBeat;

      lastBeat = millis();


      beatsPerMinute =
        60 / (delta / 1000.0);


      if (
        beatsPerMinute < 255 &&
        beatsPerMinute > 20
      ) {

        rates[rateSpot++] =
          (byte)beatsPerMinute;

        rateSpot %= RATE_SIZE;


        beatAvg = 0;

        for (
          byte x = 0;
          x < RATE_SIZE;
          x++
        ) {

          beatAvg += rates[x];
        }

        beatAvg /= RATE_SIZE;
      }


      // =================================================
      // OLED
      // =================================================

      u8g2.clearBuffer();


      // Heart

      u8g2.drawXBMP(
        2,
        2,
        24,
        21,
        beat1_bmp
      );


      // BPM

      u8g2.setFont(
        u8g2_font_ncenB08_tr
      );

      u8g2.setCursor(32, 12);
      u8g2.print("BPM");


      u8g2.setFont(
        u8g2_font_ncenB14_tr
      );

      u8g2.setCursor(32, 36);
      u8g2.print(beatAvg);


      // GSR

      u8g2.setFont(
        u8g2_font_ncenB08_tr
      );

      u8g2.setCursor(72, 12);
      u8g2.print("GSR");

      u8g2.setCursor(72, 25);
      u8g2.print(gsrValue);


      // Temperature

      u8g2.setCursor(2, 52);
      u8g2.print("T:");
      u8g2.print(objectTemperature, 1);
      u8g2.print("C");


      // Stress

      u8g2.setCursor(70, 52);
      u8g2.print(stressLevel);


      // Motion / GPS status

      u8g2.setCursor(2, 63);

      if (gpsFix) {

        u8g2.print("GPS:");
        u8g2.print(satellites);

      } else {

        u8g2.print("GPS:---");
      }


      u8g2.sendBuffer();


      // =================================================
      // SERIAL MONITOR
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
      Serial.print(stressLevel);

      Serial.print(", Object Temp=");
      Serial.print(objectTemperature, 2);

      Serial.print(" C");

      Serial.print(", Ambient Temp=");
      Serial.print(ambientTemperature, 2);

      Serial.print(" C");


      // MPU6050

      Serial.print(", ACC=");
      Serial.print(accelX, 2);
      Serial.print(",");
      Serial.print(accelY, 2);
      Serial.print(",");
      Serial.print(accelZ, 2);

      Serial.print(" g");


      Serial.print(", GYRO=");
      Serial.print(gyroX, 2);
      Serial.print(",");
      Serial.print(gyroY, 2);
      Serial.print(",");
      Serial.print(gyroZ, 2);

      Serial.print(" deg/s");


      // GPS

      if (gpsFix) {

        Serial.print(", GPS=FIX");

        Serial.print(", Lat=");
        Serial.print(latitude, 6);

        Serial.print(", Lon=");
        Serial.print(longitude, 6);

        Serial.print(", Satellites=");
        Serial.println(satellites);

      } else {

        Serial.print(", GPS=NO FIX");

        Serial.print(", Satellites=");
        Serial.println(satellites);
      }
    }
  }


  // ===================================================
  // NO FINGER
  // ===================================================

  else {

    u8g2.clearBuffer();

    u8g2.setFont(
      u8g2_font_ncenB08_tr
    );

    u8g2.drawStr(
      15,
      15,
      "Place finger"
    );

    u8g2.drawStr(
      15,
      29,
      "on MAX30105"
    );


    u8g2.setCursor(15, 43);

    u8g2.print("Temp:");
    u8g2.print(objectTemperature, 1);
    u8g2.print("C");


    u8g2.setCursor(15, 57);

    if (gpsFix) {

      u8g2.print("GPS:");
      u8g2.print(satellites);
      u8g2.print(" SAT");

    } else {

      u8g2.print("GPS searching");
    }


    u8g2.sendBuffer();


    // Serial Monitor

    Serial.print("No finger");

    Serial.print(", GSR=");
    Serial.print(gsrValue);

    Serial.print(", Stress=");
    Serial.print(stressLevel);

    Serial.print(", Object Temp=");
    Serial.print(objectTemperature, 2);

    Serial.print(" C");


    Serial.print(", ACC=");
    Serial.print(accelX, 2);
    Serial.print(",");
    Serial.print(accelY, 2);
    Serial.print(",");
    Serial.print(accelZ, 2);

    Serial.print(" g");


    Serial.print(", GYRO=");
    Serial.print(gyroX, 2);
    Serial.print(",");
    Serial.print(gyroY, 2);
    Serial.print(",");
    Serial.print(gyroZ, 2);

    Serial.print(" deg/s");


    if (gpsFix) {

      Serial.print(", GPS=FIX");

      Serial.print(", Lat=");
      Serial.print(latitude, 6);

      Serial.print(", Lon=");
      Serial.print(longitude, 6);

      Serial.print(", Satellites=");
      Serial.println(satellites);

    } else {

      Serial.print(", GPS=NO FIX");

      Serial.print(", Satellites=");
      Serial.println(satellites);
    }
  }


  delay(20);
}

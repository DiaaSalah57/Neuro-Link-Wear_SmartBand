#include <Wire.h>
#include<WiFi.h>
#include<WiFiClientSecure.h>
#include<PubSubClient.h>
#include <U8g2lib.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <TinyGPSPlus.h>
#include <Adafruit_MLX90614.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
// =====================================================
//              WiFi & HiveMQ Cloud Credentials
// =====================================================
const char* ssid        = "Bahaa";
const char* password    = "1732001#";

const char* mqtt_server = "831c5bf5139c44d898a9ba6f0b3c526c.s1.eu.hivemq.cloud";
const int   mqtt_port   = 8883;
const char* mqtt_user   = "Neuro_link";
const char* mqtt_pass   = "smartband";

const char* TOPIC_SENSORS = "neurolink/sensors/data";
const char* TOPIC_ALERTS  = "neurolink/alerts/status";

WiFiClientSecure secureClient;
PubSubClient client(secureClient);

// =====================================================
//                       MAX30105
// =====================================================
MAX30105 particleSensor;
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute = 0.0;
int beatAvg = 0;
float bloodOxygen = 98.0; // Default SpO2 estimation

// HRV calculation variables (RMSSD)
const byte IBI_SIZE = 8;
long ibiHistory[IBI_SIZE];
byte ibiIndex = 0;
float currentHRV = 0.0;

// =====================================================
//                         GSR
// =====================================================
#define GSR_PIN 34
int gsrRaw = 0;
float gsrConductance = 0.0; // Micro-Siemens
float sweatResponse = 0.0;  // Baseline dynamic response

// =====================================================
//                     GPS NEO-6M
// =====================================================
#define GPS_RX_PIN 16
#define GPS_TX_PIN 17
TinyGPSPlus gps;
HardwareSerial GPS_Serial(2);
bool gpsFix = false;

// =====================================================
//                       MLX90614
// =====================================================
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
float objectTemperature = 0.0;

// =====================================================
//                       MPU6050
// =====================================================
Adafruit_MPU6050 mpu;
float accelX = 0.0, accelY = 0.0, accelZ = 0.0;
float gyroX = 0.0, gyroY = 0.0, gyroZ = 0.0;

// Step counter & Activity Tracking
int stepCount = 0;
float prevMag = 1.0;
unsigned long lastStepTime = 0;
String activityStatus = "Resting";

// =====================================================
//                        OLED
// =====================================================
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

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
//                 System State & Timers
// =====================================================
String serverStatus  = "NORMAL";
String serverMessage = "System Ready";

unsigned long lastMqttPublish = 0;
const unsigned long MQTT_PUBLISH_INTERVAL = 60000;

unsigned long lastDisplayUpdate = 0;
const unsigned long DISPLAY_INTERVAL = 150;

// =====================================================
//                     Helper Functions
// =====================================================
String getTimestamp() {
  if (gps.date.isValid() && gps.time.isValid()) {
    char buf[25];
    sprintf(buf, "%04d-%02d-%02dT%02d:%02d:%02dZ",
            gps.date.year(), gps.date.month(), gps.date.day(),
            gps.time.hour(), gps.time.minute(), gps.time.second());
    return String(buf);
  }
  return "2026-09-27T12:00:00Z"; // Fallback timestamp
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String incomingMessage = "";
  for (unsigned int i = 0; i < length; i++) {
    incomingMessage += (char)payload[i];
  }

  int delimiterIndex = incomingMessage.indexOf(',');
  if (delimiterIndex != -1) {
    serverStatus = incomingMessage.substring(0, delimiterIndex);
    serverMessage = incomingMessage.substring(delimiterIndex + 1);
  } else {
    serverStatus = incomingMessage;
    serverMessage = "";
  }
}

void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;

  if (!client.connected()) {
    String clientId = "ESP32_NeuroLink_" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      client.subscribe(TOPIC_ALERTS);
    }
  }
}

void readGPS() {
  while (GPS_Serial.available()) {
    gps.encode(GPS_Serial.read());
  }
  gpsFix = gps.location.isValid();
}

void readTemperature() {
  float temp = mlx.readObjectTempC();
  if (!isnan(temp) && temp > 15.0 && temp < 50.0) {
    objectTemperature = temp;
  }
}

void readMPU6050() {
  sensors_event_t accel, gyro, temp;
  mpu.getEvent(&accel, &gyro, &temp);

  accelX = accel.acceleration.x / 9.80665;
  accelY = accel.acceleration.y / 9.80665;
  accelZ = accel.acceleration.z / 9.80665;

  gyroX = gyro.gyro.x;
  gyroY = gyro.gyro.y;
  gyroZ = gyro.gyro.z;

  // Compute Total Vector Magnitude for Step & Activity
  float totalAccelMag = sqrt(accelX * accelX + accelY * accelY + accelZ * accelZ);

  if (totalAccelMag > 1.35 && prevMag <= 1.35 && (millis() - lastStepTime > 300)) {
    stepCount++;
    lastStepTime = millis();
  }
  prevMag = totalAccelMag;

  // Classify Current Activity Status
  if (totalAccelMag > 1.7) {
    activityStatus = "Running";
  } else if (totalAccelMag > 1.15) {
    activityStatus = "Walking";
  } else {
    activityStatus = "Resting";
  }
}

// =====================================================
//                        SETUP
// =====================================================
void setup() {
  Serial.begin(115200);

  Wire.begin(21, 22);
  Wire.setClock(400000);

  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.drawStr(5, 25, "NeuroLink Booting");
  u8g2.drawStr(5, 45, "Connecting WiFi...");
  u8g2.sendBuffer();

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  int wifiAttempts = 0;
  while (WiFi.status() != WL_CONNECTED && wifiAttempts < 25) {
    delay(400);
    wifiAttempts++;
  }

  secureClient.setInsecure();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  client.setBufferSize(768); // Expanded buffer for detailed JSON

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    u8g2.clearBuffer();
    u8g2.drawStr(5, 30, "MAX30105 Error!");
    u8g2.sendBuffer();
    while (1);
  }
  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x1F); // Red LED enabled for SpO2 calculation
  particleSensor.setPulseAmplitudeIR(0x1F);
  particleSensor.setPulseAmplitudeGreen(0);

  pinMode(GSR_PIN, INPUT);

  mlx.begin();

  if (mpu.begin(0x68, &Wire)) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  GPS_Serial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
}

// =====================================================
//                        LOOP
// =====================================================
void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  readGPS();
  readTemperature();
  readMPU6050();

  // GSR & Sweat Response derivation
  gsrRaw = analogRead(GSR_PIN);
  gsrConductance = (4095.0 - (float)gsrRaw) * 0.025; // Transformed to uS scale
  if (gsrConductance < 0) gsrConductance = 0;
  sweatResponse = gsrConductance * 0.36;             // Normalized response

  // MAX30105 Heart Rate & HRV computation
  long irValue = particleSensor.getIR();
  long redValue = particleSensor.getRed();

  if (irValue > 50000) {
    if (checkForBeat(irValue)) {
      long delta = millis() - lastBeat;
      lastBeat = millis();
      beatsPerMinute = 60 / (delta / 1000.0);

      if (beatsPerMinute < 230 && beatsPerMinute > 30) {
        rates[rateSpot++] = (byte)beatsPerMinute;
        rateSpot %= RATE_SIZE;

        beatAvg = 0;
        for (byte x = 0; x < RATE_SIZE; x++) beatAvg += rates[x];
        beatAvg /= RATE_SIZE;

        // HRV (RMSSD calculation)
        ibiHistory[ibiIndex++] = delta;
        ibiIndex %= IBI_SIZE;

        float sumDiffSq = 0.0;
        for (byte i = 0; i < IBI_SIZE - 1; i++) {
          long diff = ibiHistory[i + 1] - ibiHistory[i];
          sumDiffSq += (float)(diff * diff);
        }
        currentHRV = sqrt(sumDiffSq / (IBI_SIZE - 1));
      }

      // Simple SpO2 estimation ratio
      if (redValue > 0 && irValue > 0) {
        float ratio = ((float)redValue / irValue);
        bloodOxygen = 110.0 - (25.0 * ratio);
        if (bloodOxygen > 100.0) bloodOxygen = 99.0;
        if (bloodOxygen < 85.0) bloodOxygen = 88.0;
      }
    }
  } else {
    beatAvg = 0;
    currentHRV = 0.0;
  }

  // Publish Payload matching the requested JSON structure every 2 seconds
  if (millis() - lastMqttPublish >= MQTT_PUBLISH_INTERVAL) {
    lastMqttPublish = millis();

    if (client.connected()) {
      String payload = "{\n";
      payload += "  \"ts\": \"" + getTimestamp() + "\",\n";
      payload += "  \"Heart_Rate\": " + String(beatAvg) + ",\n";
      payload += "  \"Body_Temperature\": " + String(objectTemperature > 0 ? objectTemperature : 36.6, 1) + ",\n";
      payload += "  \"Blood_Oxygen\": " + String(bloodOxygen, 1) + ",\n";
      payload += "  \"Step_Count\": " + String(stepCount) + ",\n";
      payload += "  \"Activity_Status\": \"" + activityStatus + "\",\n";
      payload += "  \"Accel_X\": " + String(accelX, 2) + ",\n";
      payload += "  \"Accel_Y\": " + String(accelY, 2) + ",\n";
      payload += "  \"Accel_Z\": " + String(accelZ, 2) + ",\n";
      payload += "  \"Gyro_X\": " + String(gyroX, 2) + ",\n";
      payload += "  \"Gyro_Y\": " + String(gyroY, 2) + ",\n";
      payload += "  \"Gyro_Z\": " + String(gyroZ, 2) + ",\n";
      payload += "  \"GSR_Value\": " + String(gsrConductance, 2) + ",\n";
      payload += "  \"HRV\": " + String(currentHRV, 2) + ",\n";
      payload += "  \"Sweat_Response\": " + String(sweatResponse, 2) + "\n";
      payload += "}";

      client.publish(TOPIC_SENSORS, payload.c_str());
    }
  }

  // Update OLED UI (Non-blocking)
  if (millis() - lastDisplayUpdate >= DISPLAY_INTERVAL) {
    lastDisplayUpdate = millis();

    u8g2.clearBuffer();

    if (serverStatus == "WARNING" || serverStatus == "DANGER") {
      u8g2.drawBox(0, 0, 128, 16);
      u8g2.setDrawColor(0);
      u8g2.setFont(u8g2_font_ncenB08_tr);
      u8g2.setCursor(20, 12);
      u8g2.print("! " + serverStatus + " !");

      u8g2.setDrawColor(1);
      u8g2.setCursor(2, 32);
      u8g2.print(serverMessage);

      u8g2.setCursor(2, 48);
      u8g2.print("HR:" + String(beatAvg) + " SpO2:" + String(bloodOxygen, 0) + "%");

      u8g2.setCursor(2, 62);
      u8g2.print("Act: " + activityStatus);
    } else {
      if (irValue > 50000) {
        u8g2.drawXBMP(2, 2, 24, 21, beat1_bmp);

        u8g2.setFont(u8g2_font_ncenB08_tr);
        u8g2.setCursor(30, 12);
        u8g2.print("HR");
        u8g2.setFont(u8g2_font_ncenB14_tr);
        u8g2.setCursor(30, 34);
        u8g2.print(beatAvg);

        u8g2.setFont(u8g2_font_ncenB08_tr);
        u8g2.setCursor(76, 12);
        u8g2.print("SpO2");
        u8g2.setCursor(76, 25);
        u8g2.print(String(bloodOxygen, 0) + "%");

        u8g2.setCursor(2, 48);
        u8g2.print("T:" + String(objectTemperature, 1) + "C Steps:" + String(stepCount));

        u8g2.setCursor(2, 62);
        u8g2.print("Status: " + activityStatus);
      } else {
        u8g2.setFont(u8g2_font_ncenB08_tr);
        u8g2.drawStr(10, 15, "NeuroLink Wear");
        u8g2.drawStr(10, 30, "Place Finger...");

        u8g2.setCursor(10, 46);
        u8g2.print("Temp: " + String(objectTemperature, 1) + " C");

        u8g2.setCursor(10, 62);
        u8g2.print("Steps: " + String(stepCount));
      }
    }
    u8g2.sendBuffer();
  }
}

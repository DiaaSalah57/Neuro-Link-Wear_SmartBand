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
const char* ssid        = "YOUR_WIFI_NAME";      // Enter your WiFi SSID here
const char* password    = "YOUR_WIFI_PASSWORD";  // Enter your WiFi password here

// HiveMQ Cloud Broker Credentials
const char* mqtt_server = "831c5bf5139c44d898a9ba6f0b3c526c.s1.eu.hivemq.cloud";
const int   mqtt_port   = 8883;
const char* mqtt_user   = "Neuro_link";
const char* mqtt_pass   = "smartband";

// MQTT Topics Architecture
const char* TOPIC_SENSORS = "neurolink/sensors/data";   // T1: Publishing raw sensor telemetry
const char* TOPIC_ALERTS  = "neurolink/alerts/status";  // T2: Subscribing to AI/Server alerts

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

// =====================================================
//                         GSR
// =====================================================
#define GSR_PIN 34
int gsrValue = 0;
String stressLevel = "LOW";

// =====================================================
//                     GPS NEO-6M
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
//                       MLX90614
// =====================================================
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
float objectTemperature = 0.0;
float ambientTemperature = 0.0;

// =====================================================
//                       MPU6050
// =====================================================
Adafruit_MPU6050 mpu;
float accelX = 0.0, accelY = 0.0, accelZ = 0.0;
float gyroX = 0.0, gyroY = 0.0, gyroZ = 0.0;

// =====================================================
//                        OLED
// =====================================================
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

// =====================================================
//                    HEART BITMAP
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
//                 System State & Timers
// =====================================================
String serverStatus  = "NORMAL";
String serverMessage = "System Ready";

unsigned long lastMqttPublish = 0;
const unsigned long MQTT_PUBLISH_INTERVAL = 2000; // Publish telemetry every 2 seconds

unsigned long lastDisplayUpdate = 0;
const unsigned long DISPLAY_INTERVAL = 150;       // Update OLED screen every 150ms

unsigned long lastSerialPrint = 0;
const unsigned long SERIAL_INTERVAL = 1000;       // Print to Serial every 1 second

// =====================================================
//         MQTT Callback (Receive Server Alerts)
// =====================================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String incomingMessage = "";
  for (unsigned int i = 0; i < length; i++) {
    incomingMessage += (char)payload[i];
  }

  // Expected payload format: "STATUS,MESSAGE" (e.g., "WARNING,High Stress Detected")
  int delimiterIndex = incomingMessage.indexOf(',');
  if (delimiterIndex != -1) {
    serverStatus = incomingMessage.substring(0, delimiterIndex);
    serverMessage = incomingMessage.substring(delimiterIndex + 1);
  } else {
    serverStatus = incomingMessage;
    serverMessage = "";
  }
}

// =====================================================
//                  Reconnect to MQTT
// =====================================================
void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;

  if (!client.connected()) {
    String clientId = "ESP32_NeuroLink_" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      client.subscribe(TOPIC_ALERTS);
      Serial.println("[MQTT] Connected & Subscribed to Alerts");
    } else {
      Serial.print("[MQTT] Connection failed, rc=");
      Serial.println(client.state());
    }
  }
}

// =====================================================
//                     Sensor Reads
// =====================================================
void readGPS() {
  while (GPS_Serial.available()) {
    gps.encode(GPS_Serial.read());
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

void readTemperature() {
  objectTemperature = mlx.readObjectTempC();
  ambientTemperature = mlx.readAmbientTempC();
}

void readMPU6050() {
  sensors_event_t accel, gyro, temp;
  mpu.getEvent(&accel, &gyro, &temp);

  accelX = accel.acceleration.x / 9.80665;
  accelY = accel.acceleration.y / 9.80665;
  accelZ = accel.acceleration.z / 9.80665;

  gyroX = gyro.gyro.x * 57.2958;
  gyroY = gyro.gyro.y * 57.2958;
  gyroZ = gyro.gyro.z * 57.2958;
}

// =====================================================
//                        SETUP
// =====================================================
void setup() {
  Serial.begin(115200);

  // Initialize I2C Bus
  Wire.begin(21, 22);
  Wire.setClock(400000);

  // Initialize OLED
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.drawStr(5, 25, "NeuroLink Booting");
  u8g2.drawStr(5, 45, "Connecting WiFi...");
  u8g2.sendBuffer();

  // Connect to WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  int wifiAttempts = 0;
  while (WiFi.status() != WL_CONNECTED && wifiAttempts < 25) {
    delay(400);
    wifiAttempts++;
  }

  // Setup TLS and MQTT Client
  secureClient.setInsecure(); // Skip certificate verification for cloud broker
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  client.setBufferSize(512); // Expand buffer to accommodate JSON telemetry payload

  // Initialize MAX30105
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    u8g2.clearBuffer();
    u8g2.drawStr(5, 30, "MAX30105 Error!");
    u8g2.sendBuffer();
    while (1);
  }
  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeGreen(0);

  // Initialize GSR
  pinMode(GSR_PIN, INPUT);

  // Initialize MLX90614
  if (!mlx.begin()) {
    u8g2.clearBuffer();
    u8g2.drawStr(5, 30, "MLX90614 Error!");
    u8g2.sendBuffer();
    while (1);
  }

  // Initialize MPU6050
  if (!mpu.begin(0x68, &Wire)) {
    u8g2.clearBuffer();
    u8g2.drawStr(5, 30, "MPU6050 Error!");
    u8g2.sendBuffer();
    while (1);
  }
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // Initialize GPS UART
  GPS_Serial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
}

// =====================================================
//                        LOOP
// =====================================================
void loop() {
  // Maintain MQTT Broker Connection
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  // 1. Continuous Sensor Sampling
  readGPS();
  readTemperature();
  readMPU6050();

  // 2. GSR Baseline Classification
  gsrValue = analogRead(GSR_PIN);
  if (gsrValue < 1200) {
    stressLevel = "LOW";
  } else if (gsrValue < 2000) {
    stressLevel = "MED";
  } else {
    stressLevel = "HIGH";
  }

  // 3. Heart Rate Calculation
  long irValue = particleSensor.getIR();
  if (irValue > 50000) {
    if (checkForBeat(irValue)) {
      long delta = millis() - lastBeat;
      lastBeat = millis();
      beatsPerMinute = 60 / (delta / 1000.0);

      if (beatsPerMinute < 255 && beatsPerMinute > 20) {
        rates[rateSpot++] = (byte)beatsPerMinute;
        rateSpot %= RATE_SIZE;

        beatAvg = 0;
        for (byte x = 0; x < RATE_SIZE; x++) {
          beatAvg += rates[x];
        }
        beatAvg /= RATE_SIZE;
      }
    }
  } else {
    beatAvg = 0;
  }

  // 4. Publish Telemetry via MQTT (T1) every 2 seconds
  if (millis() - lastMqttPublish >= MQTT_PUBLISH_INTERVAL) {
    lastMqttPublish = millis();

    if (client.connected()) {
      String payload = "{";
      payload += "\"bpm\":" + String(beatAvg) + ",";
      payload += "\"gsr\":" + String(gsrValue) + ",";
      payload += "\"ir\":" + String(irValue) + ",";
      payload += "\"temp\":" + String(objectTemperature, 2) + ",";
      payload += "\"ax\":" + String(accelX, 2) + ",";
      payload += "\"ay\":" + String(accelY, 2) + ",";
      payload += "\"az\":" + String(accelZ, 2) + ",";
      payload += "\"fix\":" + String(gpsFix ? 1 : 0) + ",";
      payload += "\"lat\":" + String(latitude, 6) + ",";
      payload += "\"lng\":" + String(longitude, 6);
      payload += "}";

      client.publish(TOPIC_SENSORS, payload.c_str());
    }
  }

  // 5. Update OLED UI (Non-blocking)
  if (millis() - lastDisplayUpdate >= DISPLAY_INTERVAL) {
    lastDisplayUpdate = millis();

    u8g2.clearBuffer();

    if (serverStatus == "WARNING" || serverStatus == "DANGER") {
      // Emergency / Alert UI Triggered by AI Server
      u8g2.drawBox(0, 0, 128, 16);
      u8g2.setDrawColor(0); // Inverted text color
      u8g2.setFont(u8g2_font_ncenB08_tr);
      u8g2.setCursor(20, 12);
      u8g2.print("! " + serverStatus + " !");

      u8g2.setDrawColor(1); // Normal color
      u8g2.setCursor(2, 32);
      u8g2.print(serverMessage);

      u8g2.setCursor(2, 48);
      u8g2.print("BPM:" + String(beatAvg) + " T:" + String(objectTemperature, 1) + "C");

      u8g2.setCursor(2, 62);
      u8g2.print(gpsFix ? "Loc Sent (GPS OK)" : "Loc: Acquiring...");
    } else {
      // Normal Vital Signs UI
      if (irValue > 50000) {
        u8g2.drawXBMP(2, 2, 24, 21, beat1_bmp);

        u8g2.setFont(u8g2_font_ncenB08_tr);
        u8g2.setCursor(30, 12);
        u8g2.print("BPM");
        u8g2.setFont(u8g2_font_ncenB14_tr);
        u8g2.setCursor(30, 34);
        u8g2.print(beatAvg);

        u8g2.setFont(u8g2_font_ncenB08_tr);
        u8g2.setCursor(76, 12);
        u8g2.print("GSR");
        u8g2.setCursor(76, 25);
        u8g2.print(gsrValue);

        u8g2.setCursor(2, 48);
        u8g2.print("T:" + String(objectTemperature, 1) + "C");

        u8g2.setCursor(65, 48);
        u8g2.print("S:" + stressLevel);

        u8g2.setCursor(2, 62);
        u8g2.print(gpsFix ? "GPS:" + String(satellites) + " SAT" : "GPS: Search");
      } else {
        u8g2.setFont(u8g2_font_ncenB08_tr);
        u8g2.drawStr(10, 15, "NeuroLink Wear");
        u8g2.drawStr(10, 30, "Place Finger...");

        u8g2.setCursor(10, 46);
        u8g2.print("Temp: " + String(objectTemperature, 1) + " C");

        u8g2.setCursor(10, 62);
        u8g2.print(gpsFix ? "GPS Ready" : "GPS Searching...");
      }
    }
    u8g2.sendBuffer();
  }

  // 6. Serial Telemetry Logging
  if (millis() - lastSerialPrint >= SERIAL_INTERVAL) {
    lastSerialPrint = millis();
    Serial.print("BPM: "); Serial.print(beatAvg);
    Serial.print(" | GSR: "); Serial.print(gsrValue);
    Serial.print(" | Temp: "); Serial.print(objectTemperature, 1);
    Serial.print(" | AccelZ: "); Serial.print(accelZ, 2);
    Serial.print(" | GPS Fix: "); Serial.print(gpsFix ? "YES" : "NO");
    Serial.print(" | AI Status: "); Serial.println(serverStatus);
  }
}

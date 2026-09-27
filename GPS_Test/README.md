# GPS NEO-6M Test (ESP32)

Standalone sketch to verify the u-blox **NEO-6M** GPS module before adding it to
the main `Smart_band` firmware.

## Wiring

| NEO-6M | ESP32 DevKit |
|--------|--------------|
| VCC    | 5V (or 3V3)  |
| GND    | GND          |
| TX     | GPIO16 (RX2) |
| RX     | GPIO17 (TX2) |

GPS TX is 3.3 V logic → no level shifter needed. GPIO16/17 are free (the smart
band uses GPIO21/22 for I²C and GPIO34 for GSR), so this can be merged into the
main sketch later without pin conflicts.

## Library

Arduino Library Manager → **TinyGPSPlus** by Mikal Hart.

## Usage

1. Open `GPS_Test.ino`, select board *ESP32 Dev Module*, upload.
2. Open Serial Monitor at **115200 baud**.
3. Put the antenna outdoors / by a window. The red LED on the module starts
   blinking (1 Hz) once it has a fix — cold start takes 30 s to ~2 min.

Expected output once locked:

```
------------- GPS STATUS -------------
Satellites : 7
HDOP       : 1.20
Latitude   : 30.044420
Longitude  : 31.235712
Google Maps: https://maps.google.com/?q=30.044420,31.235712
Altitude   : 28.4 m
Speed      : 0.31 km/h
UTC Date   : 27/09/2026
UTC Time   : 14:03:11
Chars RX   : 18422 | Sentences OK: 210 | Checksum err: 0
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `[ERROR] No data from GPS module!` | GPS **TX** must go to ESP32 **GPIO16**; check common GND and power. |
| Garbage characters | Wrong baud rate — try 4800 / 38400 by changing `GPS_BAUD`. |
| Data arrives but `no fix yet` | Normal indoors. Wait outside; check the ceramic antenna is connected. |
| Want to see raw NMEA | Set `#define RAW_MODE true` and re-upload. |

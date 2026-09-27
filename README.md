# NeuroLink Wear

AI-powered IoT wearable that monitors vital signs, detects abnormal health trajectories early
and escalates emergencies to caregivers.

| Part | Where |
|---|---|
| ESP32 firmware (sensors, edge features, fall/SOS safety workflow, MQTT/TLS) | [`Smart_band/`](Smart_band/README.md) |
| Backend (FastAPI + MQTT bridge + anomaly pipeline) | `main.py`, `pipeline.py`, `models/` |
| Live dashboard | `dashboard.html` |
| Training data | `Smartbandproject_dataset_finalll.csv` |

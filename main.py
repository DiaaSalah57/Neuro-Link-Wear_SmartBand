import json
import asyncio
import threading
from pathlib import Path
from typing import Set

import paho.mqtt.client as mqtt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from pipeline import process_reading

# ── Config ────────────────────────────────────────────────────────────────────
MQTT_BROKER = "localhost"   # change to HiveMQ host if using cloud broker
MQTT_PORT   = 1883
MQTT_TOPIC  = "neurolink/sensors"

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="NeuroLink Wear API")

# ── WebSocket manager ─────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.active -= dead

manager = ConnectionManager()

# ── MQTT → async bridge ───────────────────────────────────────────────────────
message_queue: asyncio.Queue = asyncio.Queue()
loop: asyncio.AbstractEventLoop = None  # captured on startup

def on_mqtt_message(client, userdata, msg):
    """Runs in paho thread. Forwards to async queue."""
    try:
        raw = json.loads(msg.payload.decode())
        asyncio.run_coroutine_threadsafe(message_queue.put(raw), loop)
    except Exception as e:
        print(f"[MQTT] Parse error: {e}")

def start_mqtt():
    client = mqtt.Client()
    client.on_message = on_mqtt_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(MQTT_TOPIC)
    print(f"[MQTT] Subscribed to {MQTT_TOPIC} on {MQTT_BROKER}:{MQTT_PORT}")
    client.loop_forever()

# ── Background worker: queue → pipeline → broadcast ───────────────────────────
async def pipeline_worker():
    while True:
        raw = await message_queue.get()
        try:
            result = process_reading(raw)
            await manager.broadcast(result)
            status = result['ensemble']
            if status != 'Normal':
                print(f"[ALERT] {status} — {result['condition']}")
        except Exception as e:
            print(f"[Pipeline] Error: {e}")

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global loop
    loop = asyncio.get_event_loop()
    threading.Thread(target=start_mqtt, daemon=True).start()
    asyncio.create_task(pipeline_worker())
    print("[Server] NeuroLink Wear API started.")

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def dashboard():
    return HTMLResponse(Path("dashboard.html").read_text())

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()   # keep-alive ping
    except WebSocketDisconnect:
        manager.disconnect(ws)

@app.post("/simulate")
async def simulate(raw: dict):
    """
    Test endpoint — bypasses MQTT, send a reading directly.
    Useful for testing the pipeline without the ESP32.

    Example body:
    {
        "Heart_Rate": 101, "Body_Temperature": 37.3, "Blood_Oxygen": 97.1,
        "HRV": 17.4, "GSR_Value": 0.84, "Sweat_Response": 0.6,
        "Step_Count": 0, "Accel_X": 0.1, "Accel_Y": 0.0, "Accel_Z": 1.0,
        "Gyro_X": 0.02, "Gyro_Y": 0.01, "Gyro_Z": 0.0
    }
    """
    result = process_reading(raw)
    await manager.broadcast(result)
    return result

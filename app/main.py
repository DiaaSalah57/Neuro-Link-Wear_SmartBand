"""
NeuroLink Wear — FastAPI application.

Serves the SPA dashboard, the REST API and the real-time WebSocket stream.
On startup the SQLite database is created + seeded and the telemetry simulator
starts pumping live readings (swap in real hardware via /api/telemetry/ingest
or the MQTT bridge without touching the frontend).
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .auth import bootstrap_secret, decode_token
from .db import get_db, one
from .seed import seed_all
from .db import init_db
from .simulator import get_simulator

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"


# ── WebSocket connection manager ─────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: dict):
        dead = set()
        for ws in list(self.active):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.add(ws)
        self.active -= dead


manager = ConnectionManager()


async def on_simulator_message(message: dict):
    await manager.broadcast(message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    bootstrap_secret()
    seed_all()

    # Keep the vitals table lean — drop data older than 30 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as db:
        db.execute("DELETE FROM vitals WHERE ts<?", (cutoff,))
        db.execute("DELETE FROM location_history WHERE ts<?", (cutoff,))

    sim = get_simulator(on_message=on_simulator_message)
    task = asyncio.create_task(sim.run())
    print("[NeuroLink Wear] API + dashboard ready — simulator streaming.")
    yield
    task.cancel()


app = FastAPI(
    title="NeuroLink Wear — Health & Safety Monitoring",
    description="Real-time IoT health & safety dashboard for elderly care, integrated with the NeuroLink Wear smart band.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.middleware("http")
async def no_stale_assets(request, call_next):
    """
    Never let a browser or proxy serve stale SPA code — stale JS was the root
    cause of a sign-in loop (old client missing the proxy-proof auth path).
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static") or path == "/" or path.endswith(".js") or path.endswith(".css"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/api/health")
def health():
    with get_db() as db:
        dev = one(db.execute("SELECT online,last_seen,battery FROM devices WHERE id=1"))
    return {"status": "ok", "device": dev, "time": datetime.now(timezone.utc).isoformat()}


# ── WebSocket ────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token", "")
    if not decode_token(token):
        await ws.close(code=4401)
        return
    await manager.connect(ws)
    # Greet with the freshest reading so the UI renders instantly
    with get_db() as db:
        latest = one(db.execute("SELECT * FROM vitals ORDER BY ts DESC, id DESC LIMIT 1"))
        dev = one(db.execute("SELECT id,name,model,serial,battery,charging,online,status,last_seen FROM devices WHERE id=1"))
    if latest:
        latest["device"] = dev
        await ws.send_text(json.dumps({"type": "telemetry", "data": latest}))
    await ws.send_text(json.dumps({"type": "hello", "data": {"device": dev}}))
    try:
        while True:
            raw = await ws.receive_text()
            if raw == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


# ── Static SPA ───────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(404)
async def not_found(request, exc):
    if request.url.path.startswith("/api"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return FileResponse(STATIC / "index.html")

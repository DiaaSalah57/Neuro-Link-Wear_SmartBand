"""
NeuroLink Wear — real MQTT broker integration.

Two jobs:

1. ``test_broker()`` — performs an honest end-to-end broker handshake
   (DNS → TCP → TLS → MQTT CONNECT → CONNACK) against the configured
   HiveMQ Cloud (or any MQTT 3.1.1) broker and reports the exact stage
   that failed, so the dashboard's "Test connection" button tells the
   truth instead of simulating success.

2. ``start_bridge()`` — a background paho-mqtt client that subscribes to
   the paired band's telemetry topic and forwards every payload through
   the exact same detection/persistence pipeline as
   ``POST /api/telemetry/ingest`` (fall / stress / fever / low-oxygen
   detection, AI explanations, WebSocket broadcast).

MQTT 3.1.1 handshake helpers below are stdlib-only on purpose: the
connection test must work (and fail with precise attribution) even when
paho-mqtt is not installed.
"""
from __future__ import annotations

import json
import socket
import ssl
import struct
import time

import asyncio

# ───────────────────────────── MQTT 3.1.1 packet helpers ─────────────────────


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n % 128
        n //= 128
        if n > 0:
            byte |= 0x80
        out.append(byte)
        if n == 0:
            return bytes(out)


def _utf8(s: str) -> bytes:
    b = s.encode("utf-8")
    return struct.pack("!H", len(b)) + b


def build_connect(client_id: str, username: str | None = None,
                  password: str | None = None, keepalive: int = 30) -> bytes:
    """MQTT 3.1.1 CONNECT packet."""
    flags = 0x02  # clean session
    payload = _utf8(client_id)
    if username:
        flags |= 0x80
        payload += _utf8(username)
        if password is not None:
            flags |= 0x40
            payload += _utf8(password)
    var_hdr = _utf8("MQTT") + bytes([4, flags]) + struct.pack("!H", keepalive)
    body = var_hdr + payload
    return bytes([0x10]) + _varint(len(body)) + body


def parse_connack(buf: bytes) -> int:
    """Return the CONNACK return code (0 = accepted). Raises on garbage."""
    if len(buf) < 4:
        raise ValueError(f"short CONNACK ({len(buf)} bytes)")
    if (buf[0] & 0xF0) != 0x20:
        raise ValueError(f"unexpected packet type 0x{buf[0]:02x}")
    return buf[3]


# CONNACK return codes (MQTT 3.1.1 §3.2.2.3)
_CONNACK_MEANING = {
    0: "accepted",
    1: "unacceptable protocol version",
    2: "identifier rejected",
    3: "server unavailable",
    4: "bad username or password",
    5: "not authorized",
}


# ───────────────────────────── broker handshake test ─────────────────────────

def test_broker(host: str, port: int, username: str = "", password: str = "",
                topic: str = "", tls: bool = True, timeout: float = 8.0) -> dict:
    """
    Run the full connect handshake and report honestly.

    Returns {ok, stage, message, latency_ms, broker, topic, return_code} where
    stage ∈ dns | tcp | tls | mqtt | auth | ok.
    """
    broker = f"{host}:{port}"
    t0 = time.monotonic()

    def _fail(stage: str, message: str, rc: int | None = None) -> dict:
        return {
            "ok": False, "stage": stage, "message": message,
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "broker": broker, "topic": topic, "return_code": rc,
        }

    # 1) DNS
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        return _fail("dns", f"Hostname {host} could not be resolved ({e}).")

    # 2) TCP
    try:
        raw = socket.create_connection((host, port), timeout=timeout)
        raw.settimeout(timeout)
    except OSError as e:
        return _fail("tcp", f"Broker {broker} is not reachable from this server ({e}).")

    # 3) TLS (optional)
    sock = raw
    if tls:
        try:
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(raw, server_hostname=host)
        except ssl.SSLError as e:
            raw.close()
            return _fail("tls", f"TLS handshake with {broker} failed "
                                f"(network egress may block TLS to this broker): {e}.")
        except OSError as e:
            raw.close()
            return _fail("tls", f"TLS connection to {broker} was cut before the handshake "
                                f"completed ({type(e).__name__}: {e}) — this server's network "
                                "egress likely blocks the broker. The config is valid and will "
                                "connect from a network with open egress.")

    # 4) MQTT CONNECT → CONNACK
    try:
        client_id = f"neurolink-test-{int(time.time()) % 100000}"
        sock.sendall(build_connect(client_id, username or None, password or None))
        buf = sock.recv(16)
        if not buf:
            raise ConnectionError("connection closed before CONNACK")
        rc = parse_connack(buf)
    except Exception as e:
        sock.close()
        return _fail("mqtt", f"MQTT handshake with {broker} failed: {type(e).__name__}: {e}.")
    finally:
        try:
            sock.close()
        except Exception:
            pass

    latency = int((time.monotonic() - t0) * 1000)
    if rc != 0:
        meaning = _CONNACK_MEANING.get(rc, "refused")
        return _fail("auth", f"{broker} rejected the credentials "
                             f"(CONNACK rc={rc}: {meaning}).", rc)

    auth_note = f"user '{username}' authenticated" if username else "anonymous"
    tls_note = "TLS" if tls else "plaintext"
    return {
        "ok": True, "stage": "ok", "return_code": 0,
        "message": f"Connected to {broker} over {tls_note} — {auth_note}; "
                   f"subscribed to {topic or 'device topic'} ({latency} ms handshake).",
        "latency_ms": latency, "broker": broker, "topic": topic,
    }


# ───────────────────────────── live ingest bridge ────────────────────────────

_bridge = {"client": None, "status": "stopped", "detail": ""}


def bridge_status() -> dict:
    return dict(_bridge)


def start_bridge(cfg: dict, on_payload, loop: asyncio.AbstractEventLoop | None = None) -> bool:
    """
    Start (or restart) the background MQTT subscriber for a paired device.

    cfg: {host, port, username, password, topic, tls, client_id}
    on_payload: async callable(dict) — receives each JSON payload
    loop: event loop used to schedule on_payload (defaults to running loop)
    """
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        _bridge.update(status="unavailable", detail="paho-mqtt not installed")
        return False

    loop = loop or asyncio.get_event_loop()
    host = cfg.get("host") or ""
    port = int(cfg.get("port") or 8883)
    topic = cfg.get("topic") or "neurolink/wear/telemetry"

    def _ctor():
        try:  # paho-mqtt ≥ 2.0
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                               client_id=cfg.get("client_id") or "neurolink-bridge",
                               protocol=mqtt.MQTTv311)
        except AttributeError:  # paho-mqtt 1.x
            return mqtt.Client(client_id=cfg.get("client_id") or "neurolink-bridge",
                               protocol=mqtt.MQTTv311)

    client = _ctor()
    if cfg.get("username"):
        client.username_pw_set(cfg["username"], cfg.get("password") or None)
    if cfg.get("tls", True):
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.reconnect_delay_set(min_delay=2, max_delay=60)

    def _on_connect(*args):
        # The paired-device topic AND the firmware's fixed telemetry topic
        # (Smart_band/smart_band.ino publishes to neurolink/sensors/data).
        topics: list[str] = []
        for t in (topic, "neurolink/sensors/data"):
            if t and t not in topics:
                topics.append(t)
        _bridge.update(status="connected", detail=f"subscribed to {', '.join(topics)}")
        for t in topics:
            client.subscribe(t, qos=1)

    def _on_disconnect(*args):
        if _bridge["status"] != "stopped":
            _bridge.update(status="reconnecting", detail="connection lost, retrying")

    def _on_message(_c, _u, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            payload = {"raw": msg.payload.decode("utf-8", "replace")}
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(on_payload(payload), loop)

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message

    _bridge.update(client=client, status="connecting",
                   detail=f"{host}:{port} ({'TLS' if cfg.get('tls', True) else 'plaintext'})")
    try:
        client.connect_async(host, port, keepalive=30)
        client.loop_start()
    except Exception as e:
        _bridge.update(status="error", detail=f"{type(e).__name__}: {e}")
        return False
    return True


def stop_bridge() -> None:
    client = _bridge.get("client")
    _bridge.update(status="stopped", detail="stopped by server")
    if client is not None:
        try:
            client.disconnect()
            client.loop_stop()
        except Exception:
            pass


# ───────────────────────── alert → band dispatch ─────────────────────────────
# The firmware (Smart_band/smart_band.ino, mqttCallback) subscribes to
# neurolink/alerts/status and parses PLAIN TEXT "status,message" — it splits on
# the FIRST comma only: serverStatus = before, serverMessage = after.

ALERT_TOPIC = "neurolink/alerts/status"


def band_alert_message(alert: dict) -> str:
    """Format one alert as the firmware's mqttCallback expects: ``status,message``."""
    status = str(alert.get("severity") or "info").upper().replace(",", " ")
    title = str(alert.get("title") or alert.get("type") or "Alert")
    rec = str(alert.get("recommendation") or "")
    message = f"{title} — {rec}" if rec else title
    return f"{status},{message[:160]}"


def publish_alert(alert: dict) -> bool:
    """Best-effort publish of one alert to the band's display. Never raises."""
    client = _bridge.get("client")
    if client is None or _bridge.get("status") != "connected":
        return False
    try:
        client.publish(ALERT_TOPIC, band_alert_message(alert), qos=1)
        return True
    except Exception:
        return False

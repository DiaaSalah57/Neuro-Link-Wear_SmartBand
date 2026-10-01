/**
 * NeuroLink Wear — WebSocket client with auto-reconnect, offline fallback,
 * and direct browser MQTT-over-WSS bridge when backend egress is restricted.
 */
import { auth } from './api.js?v=20261001-7';

const listeners = new Set();
let ws = null;
let tries = 0;
let closedByUser = false;
let pollTimer = null;
let mqttWs = null;
let mqttPingTimer = null;
let mqttActiveKey = '';

export const wsState = {
  connected: false,
  mqttConnected: false,
  get reconnecting() { return !this.connected && !closedByUser; },
};

function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}/ws?token=${encodeURIComponent(auth.token)}`;
}

function emit(message) {
  listeners.forEach((fn) => {
    try {
      const r = fn(message);
      if (r && typeof r.catch === 'function') r.catch((e) => console.error('[ws listener]', e));
    } catch (e) { console.error('[ws listener]', e); }
  });
}

/* ── Minimal MQTT 3.1.1 over WSS bridge (for cloud preview environments) ── */
const enc = new TextEncoder();
const dec = new TextDecoder();

function mqttUtf8(str) {
  const b = enc.encode(str || '');
  const out = new Uint8Array(2 + b.length);
  out[0] = (b.length >> 8) & 0xff;
  out[1] = b.length & 0xff;
  out.set(b, 2);
  return out;
}

function mqttVarint(n) {
  const out = [];
  do {
    let byte = n % 128;
    n = Math.floor(n / 128);
    if (n > 0) byte |= 0x80;
    out.push(byte);
  } while (n > 0);
  return new Uint8Array(out);
}

function concatBytes(...arrays) {
  const len = arrays.reduce((s, a) => s + a.length, 0);
  const out = new Uint8Array(len);
  let off = 0;
  for (const a of arrays) { out.set(a, off); off += a.length; }
  return out;
}

function buildMqttConnect(clientId, username, password, keepalive = 30) {
  let flags = 0x02; // clean session
  const parts = [mqttUtf8(clientId)];
  if (username) {
    flags |= 0x80;
    parts.push(mqttUtf8(username));
    if (password !== undefined && password !== null) {
      flags |= 0x40;
      parts.push(mqttUtf8(password));
    }
  }
  const varHdr = concatBytes(
    mqttUtf8('MQTT'),
    new Uint8Array([4, flags, (keepalive >> 8) & 0xff, keepalive & 0xff]),
  );
  const body = concatBytes(varHdr, ...parts);
  return concatBytes(new Uint8Array([0x10]), mqttVarint(body.length), body);
}

function buildMqttSubscribe(pktId, topics) {
  const varHdr = new Uint8Array([(pktId >> 8) & 0xff, pktId & 0xff]);
  const subParts = topics.map((t) => concatBytes(mqttUtf8(t), new Uint8Array([0x01])));
  const body = concatBytes(varHdr, ...subParts);
  return concatBytes(new Uint8Array([0x82]), mqttVarint(body.length), body);
}

function stopBrowserMqtt() {
  if (mqttPingTimer) { clearInterval(mqttPingTimer); mqttPingTimer = null; }
  if (mqttWs) {
    try { mqttWs.onclose = null; mqttWs.close(); } catch { /* noop */ }
    mqttWs = null;
  }
  wsState.mqttConnected = false;
  mqttActiveKey = '';
}

function ensureBrowserMqttBridge(dev) {
  if (!dev || !dev.mqtt_host || dev.bridge_status === 'connected') return;
  const host = dev.mqtt_host;
  const topic = dev.mqtt_topic || 'neurolink/sensors/data';
  const username = dev.mqtt_username || 'Neuro_link';
  const password = dev.mqtt_password || 'smartband';
  const key = `${host}|${topic}|${username}`;
  if (mqttWs && mqttActiveKey === key && mqttWs.readyState <= 1) return;

  stopBrowserMqtt();
  mqttActiveKey = key;

  try {
    mqttWs = new WebSocket(`wss://${host}:8884/mqtt`, 'mqtt');
    mqttWs.binaryType = 'arraybuffer';
  } catch {
    return;
  }

  mqttWs.onopen = () => {
    const cid = `neurolink-web-${Math.random().toString(16).slice(2, 8)}`;
    mqttWs.send(buildMqttConnect(cid, username, password, 30));
    mqttPingTimer = setInterval(() => {
      if (mqttWs && mqttWs.readyState === 1) {
        mqttWs.send(new Uint8Array([0xc0, 0x00])); // PINGREQ
      }
    }, 20000);
  };

  mqttWs.onmessage = async (evt) => {
    const buf = new Uint8Array(evt.data);
    let pos = 0;
    while (pos < buf.length) {
      const b0 = buf[pos];
      const type = b0 & 0xf0;
      let remLen = 0, mult = 1, idx = pos + 1;
      while (idx < buf.length) {
        const b = buf[idx++];
        remLen += (b & 0x7f) * mult;
        mult *= 128;
        if ((b & 0x80) === 0) break;
      }
      const pktEnd = idx + remLen;
      if (type === 0x20 && remLen >= 2 && buf[idx + 1] === 0) {
        // CONNACK accepted -> subscribe to configured topic & firmware topic
        wsState.mqttConnected = true;
        const topics = Array.from(new Set([topic, 'neurolink/sensors/data'].filter(Boolean)));
        mqttWs.send(buildMqttSubscribe(1, topics));
      } else if (type === 0x30 && pktEnd <= buf.length) {
        // PUBLISH frame
        const qos = (b0 >> 1) & 0x03;
        const tLen = (buf[idx] << 8) | buf[idx + 1];
        let pIdx = idx + 2 + tLen;
        if (qos > 0) {
          const pktId = (buf[pIdx] << 8) | buf[pIdx + 1];
          pIdx += 2;
          if (qos === 1 && mqttWs && mqttWs.readyState === 1) {
            mqttWs.send(new Uint8Array([0x40, 0x02, (pktId >> 8) & 0xff, pktId & 0xff]));
          }
        }
        const rawStr = dec.decode(buf.subarray(pIdx, pktEnd));
        try {
          const payload = JSON.parse(rawStr);
          await fetch(`/api/telemetry/ingest?access_token=${encodeURIComponent(auth.token)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Auth-Token': auth.token },
            body: JSON.stringify(payload),
          });
        } catch (err) {
          console.error('[mqtt-wss ingest]', err);
        }
      }
      pos = pktEnd > pos ? pktEnd : buf.length;
    }
  };

  mqttWs.onclose = () => {
    wsState.mqttConnected = false;
    if (mqttPingTimer) { clearInterval(mqttPingTimer); mqttPingTimer = null; }
    mqttActiveKey = '';
  };
  mqttWs.onerror = () => { try { mqttWs.close(); } catch { /* noop */ } };
}

function startPollFallback() {
  // When the socket cannot connect, poll the REST API so the UI stays alive.
  if (pollTimer) return;
  pollTimer = setInterval(async () => {
    try {
      const mod = await import('./api.js?v=20261001-7');
      const latest = await mod.api.latest();
      if (latest && latest.device) ensureBrowserMqttBridge(latest.device);
      if (latest && latest.heart_rate !== undefined && latest.heart_rate !== null) {
        emit({ type: 'telemetry', data: latest });
      }
      emit({ type: 'device_status', data: latest.device || {} });
    } catch { /* server briefly unavailable */ }
  }, 4000);
}
function stopPollFallback() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

export function connectWS() {
  if (!auth.token) return;
  closedByUser = false;
  try {
    ws = new WebSocket(wsUrl());
  } catch (e) {
    startPollFallback();
    return;
  }

  ws.onopen = () => {
    tries = 0;
    wsState.connected = true;
    stopPollFallback();
    emit({ type: 'connection', data: { connected: true } });
    const ping = setInterval(() => {
      if (ws && ws.readyState === 1) ws.send('ping');
      else clearInterval(ping);
    }, 25000);
  };

  ws.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data);
      if (msg.type === 'hello' && msg.data && msg.data.device) {
        ensureBrowserMqttBridge(msg.data.device);
      }
      emit(msg);
    } catch { /* ignore malformed */ }
  };

  ws.onclose = () => {
    wsState.connected = false;
    emit({ type: 'connection', data: { connected: false } });
    if (!closedByUser) {
      startPollFallback();
      const delay = Math.min(15000, 1000 * Math.pow(1.7, ++tries));
      setTimeout(connectWS, delay);
    }
  };

  ws.onerror = () => { try { ws.close(); } catch { /* noop */ } };
}

export function disconnectWS() {
  closedByUser = true;
  stopPollFallback();
  stopBrowserMqtt();
  if (ws) { try { ws.close(); } catch { /* noop */ } ws = null; }
}

export function onWS(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

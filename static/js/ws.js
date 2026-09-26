/**
 * NeuroLink Wear — WebSocket client with auto-reconnect + offline fallback.
 */
import { auth } from './api.js?v=20260926-6';

const listeners = new Set();
let ws = null;
let tries = 0;
let closedByUser = false;
let pollTimer = null;

export const wsState = {
  connected: false,
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

function startPollFallback() {
  // When the socket cannot connect, poll the REST API so the UI stays alive.
  if (pollTimer) return;
  pollTimer = setInterval(async () => {
    try {
      const mod = await import('./api.js?v=20260926-6');
      const latest = await mod.api.latest();
      emit({ type: 'telemetry', data: latest });
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
    try { emit(JSON.parse(evt.data)); } catch { /* ignore malformed */ }
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
  if (ws) { try { ws.close(); } catch { /* noop */ } ws = null; }
}

export function onWS(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

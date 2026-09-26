/**
 * NeuroLink Wear — API client with persistent sessions.
 */
const TOKEN_KEY = 'nlw_token';
const USER_KEY = 'nlw_user';

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY) || ''; },
  get user() {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  },
  set(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, { method = 'GET', body, query } = {}) {
  let url = `/api${path}`;
  if (query) {
    const qs = new URLSearchParams();
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v);
    });
    const s = qs.toString();
    if (s) url += `?${s}`;
  }
  const headers = { 'Content-Type': 'application/json' };
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;

  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && !path.startsWith('/auth/login')) {
    auth.clear();
    window.dispatchEvent(new CustomEvent('nlw:logout'));
    throw new ApiError(401, 'Session expired — please sign in again');
  }
  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  if (!res.ok) {
    throw new ApiError(res.status, (data && data.detail) || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  // auth
  login: (email, password) => request('/auth/login', { method: 'POST', body: { email, password } }),
  me: () => request('/auth/me'),
  // patient
  patient: () => request('/patient'),
  updatePatient: (body) => request('/patient', { method: 'PUT', body }),
  // telemetry
  latest: () => request('/telemetry/latest'),
  history: (hours = 24, maxPoints = 420) => request('/telemetry/history', { query: { hours, max_points: maxPoints } }),
  activity: (days = 14) => request('/telemetry/activity', { query: { days } }),
  // alerts
  alerts: (params = {}) => request('/alerts', { query: params }),
  alertsSummary: () => request('/alerts/summary'),
  acknowledgeAlert: (id) => request(`/alerts/${id}/acknowledge`, { method: 'POST' }),
  resolveAlert: (id) => request(`/alerts/${id}/resolve`, { method: 'POST' }),
  sos: (note) => request('/alerts/sos', { method: 'POST', body: { note } }),
  // AI
  summaries: (limit = 10) => request('/ai/summaries', { query: { limit } }),
  generateSummary: () => request('/ai/summaries/generate', { method: 'POST' }),
  // dispatch
  dispatch: (payload) => request('/dispatch', { method: 'POST', body: payload }),
  dispatches: (alertId) => request('/dispatches', { query: alertId ? { alert_id: alertId } : {} }),
  // location
  locationLatest: () => request('/location/latest'),
  locationHistory: (hours = 24) => request('/location/history', { query: { hours } }),
  // contacts
  contacts: () => request('/contacts'),
  createContact: (body) => request('/contacts', { method: 'POST', body }),
  updateContact: (id, body) => request(`/contacts/${id}`, { method: 'PUT', body }),
  deleteContact: (id) => request(`/contacts/${id}`, { method: 'DELETE' }),
  // devices
  devices: () => request('/devices'),
  createDevice: (body) => request('/devices', { method: 'POST', body }),
  updateDevice: (id, body) => request(`/devices/${id}`, { method: 'PUT', body }),
  deleteDevice: (id) => request(`/devices/${id}`, { method: 'DELETE' }),
  testDevice: (id) => request(`/devices/${id}/test-connection`, { method: 'POST' }),
  // thresholds
  thresholds: () => request('/thresholds'),
  updateThresholds: (body) => request('/thresholds', { method: 'PUT', body }),
  // stats
  stats: () => request('/stats/overview'),
  // users
  users: () => request('/users'),
  createUser: (body) => request('/users', { method: 'POST', body }),
  updateUser: (id, body) => request(`/users/${id}`, { method: 'PUT', body }),
  deleteUser: (id) => request(`/users/${id}`, { method: 'DELETE' }),
  // demo
  demoTrigger: (kind) => request('/demo/trigger', { method: 'POST', query: { kind } }),
};

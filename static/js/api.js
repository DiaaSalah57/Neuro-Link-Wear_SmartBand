/**
 * NeuroLink Wear — API client with persistent sessions.
 *
 * Resilience notes:
 * - Token is mirrored in-memory so a storage-blocked iframe still works.
 * - `access_token` query param is sent alongside the Authorization header so
 *   the session survives proxies that strip auth headers.
 * - A 401 only signs the user out after re-validation via /auth/me — a single
 *   transient failure never bounces the dashboard back to the login screen.
 */
const TOKEN_KEY = 'nlw_token';
const USER_KEY = 'nlw_user';

// In-memory fallback (storage can throw in sandboxed iframes)
let memToken = '';
let memUser = null;

function safeGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function safeSet(key, val) {
  try { localStorage.setItem(key, val); } catch { /* memory-only session */ }
}
function safeDel(key) {
  try { localStorage.removeItem(key); } catch { /* noop */ }
}

export const auth = {
  get token() { return safeGet(TOKEN_KEY) || memToken; },
  get user() {
    if (memUser) return memUser;
    try {
      const raw = safeGet(USER_KEY);
      memUser = raw ? JSON.parse(raw) : null;
    } catch { memUser = null; }
    return memUser;
  },
  set(token, user) {
    memToken = token || '';
    memUser = user || null;
    safeSet(TOKEN_KEY, token || '');
    safeSet(USER_KEY, JSON.stringify(user || null));
  },
  clear() {
    memToken = '';
    memUser = null;
    safeDel(TOKEN_KEY);
    safeDel(USER_KEY);
  },
};

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

function buildUrl(path, query) {
  let url = `/api${path}`;
  const qs = new URLSearchParams();
  if (query) {
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v);
    });
  }
  // Proxy-proof auth: header AND query parameter carry the same token.
  // Never attach the token to login attempts (a stale one must not matter).
  if (auth.token && path !== '/auth/login') qs.set('access_token', auth.token);
  const s = qs.toString();
  return s ? `${url}?${s}` : url;
}

async function rawFetch(path, { method = 'GET', body, query, authed = true } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (authed && auth.token && path !== '/auth/login') headers.Authorization = `Bearer ${auth.token}`;
  return fetch(buildUrl(path, query), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

/** Re-validate the session without triggering the logout side-effect. */
async function sessionIsReallyDead() {
  try {
    const res = await rawFetch('/auth/me');
    return res.status === 401 || res.status === 403;
  } catch {
    return false; // network hiccup — do NOT sign the user out
  }
}

let revalidating = false;
async function handle401(path) {
  if (path === '/auth/me' || revalidating) {
    auth.clear();
    window.dispatchEvent(new CustomEvent('nlw:logout'));
    return;
  }
  revalidating = true;
  const dead = await sessionIsReallyDead();
  revalidating = false;
  if (dead) {
    auth.clear();
    window.dispatchEvent(new CustomEvent('nlw:logout'));
  }
}

async function request(path, { method = 'GET', body, query } = {}) {
  let res;
  try {
    res = await rawFetch(path, { method, body, query });
  } catch (e) {
    throw new ApiError(0, 'Network error — is the server reachable?');
  }

  if (res.status === 401) {
    // A 401 from the login endpoint means bad credentials — surface the real
    // reason. It is NOT session expiry: never clear the session or log out
    // just because a sign-in attempt failed.
    if (path === '/auth/login') {
      const data = await res.json().catch(() => ({}));
      throw new ApiError(401, (data && data.detail) || 'Invalid email or password');
    }
    await handle401(path);
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
  // calibration (equation-based AI baselines)
  getCalibration: () => request('/calibration'),
  autoFitCalibration: () => request('/calibration/auto-fit', { method: 'POST', body: {} }),
  addCalibrationRef: (payload) => request('/calibration/reference', { method: 'POST', body: payload }),
  updateCalibration: (payload) => request('/calibration', { method: 'PUT', body: payload }),
  // demo
  demoTrigger: (kind) => request('/demo/trigger', { method: 'POST', query: { kind } }),
};

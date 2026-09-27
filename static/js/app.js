/**
 * NeuroLink Wear — application shell: routing, theme, sticky device banner,
 * global SOS flow and live WebSocket fan-out.
 */
import { api, auth } from './api.js?v=20260927-2';
import { store } from './store.js?v=20260927-2';
import { connectWS, disconnectWS, onWS, wsState } from './ws.js?v=20260927-2';
import {
  $, $$, esc, icons, toast, openModal, closeModal, fmtRelative, fmtDateTime,
  confirmDialog,
} from './ui.js?v=20260927-2';

import loginView from './views/login.js?v=20260927-2';
import overviewView from './views/overview.js?v=20260927-2';
import alertsView from './views/alerts.js?v=20260927-2';
import safetyView from './views/safety.js?v=20260927-2';
import trendsView from './views/trends.js?v=20260927-2';
import managementView from './views/management.js?v=20260927-2';
import settingsView from './views/settings.js?v=20260927-2';

const routes = {
  overview: overviewView,
  alerts: alertsView,
  safety: safetyView,
  trends: trendsView,
  management: managementView,
  settings: settingsView,
};

let currentView = null;
let currentRoute = null;

/* ── theme ───────────────────────────────────────────────────────────── */
function applyTheme() {
  let saved = null;
  try { saved = localStorage.getItem('nlw_theme'); } catch { /* storage blocked */ }
  if (!saved) {
    saved = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark' : 'light';
  }
  document.documentElement.dataset.theme = saved;
  $('#theme-icon-moon')?.classList.toggle('hidden', saved === 'dark');
  $('#theme-icon-sun')?.classList.toggle('hidden', saved !== 'dark');
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('nlw_theme', next); } catch { /* memory-only */ }
  $('#theme-icon-moon')?.classList.toggle('hidden', next === 'dark');
  $('#theme-icon-sun')?.classList.toggle('hidden', next !== 'dark');
}

/* ── device status banner ────────────────────────────────────────────── */
function updateBanner(device) {
  if (!device) return;
  const dot = $('#status-dot');
  const label = $('#status-label');
  const online = device.online === 1 || device.online === true;
  dot.className = `status-dot ${wsState.connected ? (online ? 'online' : 'offline') : 'connecting'}`;
  label.textContent = wsState.connected ? (online ? 'Device Online' : 'Device Offline') : 'Reconnecting…';
  $('#status-device-name').textContent = device.name || device.model || 'NeuroLink Band';
  $('#status-battery-pct').textContent = `${device.battery ?? '—'}%`;
  $('#status-sync').textContent = `last sync ${fmtRelative(device.last_seen)}`;
}

/* ── global SOS flow ─────────────────────────────────────────────────── */
async function triggerSOS() {
  const ok = await confirmDialog(
    'Trigger emergency SOS?',
    'This raises a <b>critical</b> incident immediately, shares the live GPS position and opens the dispatch panel for the emergency contact list.',
    'Yes — send SOS',
  );
  if (!ok) return;
  try {
    const alert = await api.sos();
    toast('alert', 'SOS triggered', 'Emergency incident created — dispatching contacts is the next step.', 9000);
    store.set('activeAlerts', (store.activeAlerts || 0) + 1);
    sessionStorage.setItem('nlw_dispatch_alert', JSON.stringify({ id: alert.id, title: alert.title }));
    location.hash = '#/safety?dispatch=1';
  } catch (err) {
    toast('error', 'SOS failed', err.message);
  }
}

/* ── routing ─────────────────────────────────────────────────────────── */
function parseHash() {
  const raw = location.hash.replace(/^#\/?/, '') || 'overview';
  const [path, qs] = raw.split('?');
  const params = {};
  new URLSearchParams(qs || '').forEach((v, k) => { params[k] = v; });
  return { route: routes[path] ? path : 'overview', params };
}

// Serialize navigations: a slow view render must finish (and its cleanup run)
// before the next navigation destroys/replaces it — otherwise an in-flight
// render can re-subscribe WS handlers after destroy() (null-DOM crash class).
let navChain = Promise.resolve();

function navigate() {
  navChain = navChain.then(doNavigate).catch((err) => console.error('[navigate]', err));
  return navChain;
}

async function doNavigate() {
  if (!auth.user) return;
  const { route, params } = parseHash();
  if (currentView && currentView.destroy) currentView.destroy();

  $$('#side-nav .side-link').forEach((l) => {
    l.classList.toggle('active', l.dataset.route === route);
  });
  $('#sidebar').classList.remove('open');
  $('#sidebar-overlay').classList.add('hidden');

  currentRoute = route;
  currentView = routes[route];
  const root = $('#view-root');
  root.focus();
  window.scrollTo({ top: 0 });

  try {
    await currentView.render(root, { user: auth.user, params, store });
  } catch (err) {
    console.error('[view]', err);
    root.innerHTML = `
      <div class="card card-pad">
        <h3 style="margin-bottom:8px">Something went wrong</h3>
        <p class="muted">${esc(err.message || 'Unknown error')}</p>
        <button class="btn primary" style="margin-top:12px" onclick="location.hash='#/overview'">Back to overview</button>
      </div>`;
  }
}

/* ── boot ────────────────────────────────────────────────────────────── */
let booted = false;

async function boot() {
  if (booted) return;
  booted = true;
  applyTheme();

  $('#theme-toggle').onclick = toggleTheme;
  $('#menu-btn').onclick = () => {
    $('#sidebar').classList.add('open');
    $('#sidebar-overlay').classList.remove('hidden');
  };
  const closeSidebar = () => {
    $('#sidebar').classList.remove('open');
    $('#sidebar-overlay').classList.add('hidden');
  };
  $('#sidebar-close').onclick = closeSidebar;
  $('#sidebar-overlay').onclick = closeSidebar;
  $('#sos-btn').onclick = triggerSOS;
  $('#logout-btn').onclick = () => {
    disconnectWS();
    auth.clear();
    window.dispatchEvent(new CustomEvent('nlw:logout'));
  };

  window.addEventListener('hashchange', navigate);
  window.addEventListener('nlw:sos', triggerSOS);
  window.addEventListener('nlw:login', async () => {
    try {
      await startSession();
    } catch (e) {
      console.error('[session]', e);
      toast('error', 'Could not start the session', e.message || 'Please try signing in again.');
      loginView.render();
    }
  });
  window.addEventListener('nlw:logout', () => {
    disconnectWS();
    if (currentView && currentView.destroy) currentView.destroy();
    currentView = null;
    loginView.render();
  });
  window.addEventListener('nlw:theme', () => {
    $('#theme-icon-moon')?.classList.toggle('hidden', document.documentElement.dataset.theme === 'dark');
    $('#theme-icon-sun')?.classList.toggle('hidden', document.documentElement.dataset.theme !== 'dark');
  });

  // Live WS fan-out → store + banner
  onWS(async (msg) => {
    if (msg.type === 'telemetry' && msg.data) {
      store.set('telemetry', msg.data);
      if (msg.data.device) updateBanner(msg.data.device);
    } else if (msg.type === 'hello' && msg.data && msg.data.device) {
      updateBanner(msg.data.device);
    } else if (msg.type === 'connection') {
      const dot = $('#status-dot');
      if (dot) {
        if (msg.data.connected) {
          dot.className = 'status-dot online';
          $('#status-label').textContent = 'Device Online';
          $('#status-sync').textContent = 'stream live';
        } else {
          dot.className = 'status-dot connecting';
          $('#status-label').textContent = 'Reconnecting…';
        }
      }
    } else if (msg.type === 'alert' && msg.data) {
      store.set('activeAlerts', (store.activeAlerts || 0) + 1);
      const badge = $('#nav-alert-count');
      if (badge) {
        const n = (parseInt(badge.textContent, 10) || 0) + 1;
        badge.textContent = n;
        badge.classList.remove('hidden');
      }
    }
  });

  // Attach the sign-in form handler FIRST so a native submit can never
  // reload the page, even before the session check completes.
  loginView.render();

  // Existing session? Upgrade to the dashboard, else stay on sign-in.
  if (auth.token && auth.user) {
    try {
      const me = await api.me();
      auth.set(auth.token, me);
      await startSession();
      return;
    } catch {
      auth.clear();
      loginView.render();
    }
  }
}

async function startSession() {
  const user = auth.user;
  if (!user || !auth.token) {
    loginView.render();
    return;
  }

  $('#login-screen').classList.add('hidden');
  $('#app-shell').classList.remove('hidden');

  $('#user-name').textContent = user.name || 'User';
  $('#user-role').textContent = user.role === 'admin' ? 'Administrator' : 'Caregiver';
  $('#user-avatar').textContent = (user.name || '?').split(' ').map((x) => x[0]).slice(0, 2).join('');

  // Patient chip
  api.patient().then((p) => {
    if (!p) return;
    store.set('patient', p);
    $('#patient-chip-name').textContent = p.name;
    $('#patient-chip-sub').textContent = `${p.age} · ${p.room} · NL-200`;
    $('#patient-avatar').textContent = p.name.split(' ').map((x) => x[0]).slice(0, 2).join('');
    $('#patient-avatar').style.background = p.avatar_color || 'var(--accent-2)';
  }).catch(() => { /* non-fatal — banner keeps working */ });

  // Active alert count
  api.alertsSummary().then((s) => {
    const active = s.by_status.active || 0;
    store.set('activeAlerts', active);
    const badge = $('#nav-alert-count');
    if (badge) {
      badge.textContent = active;
      badge.classList.toggle('hidden', active === 0);
    }
  }).catch(() => { /* non-fatal */ });

  api.latest().then((l) => {
    if (l && l.device) updateBanner(l.device);
  }).catch(() => { /* non-fatal */ });

  connectWS();

  // Single navigation: set the default hash without firing a second render.
  if (!location.hash || location.hash === '#' || location.hash === '#/') {
    history.replaceState(null, '', '#/overview');
  }
  await navigate();
}

// keep relative timestamps fresh
setInterval(() => {
  const el = $('#status-sync');
  if (el && store.telemetry && !el.textContent.includes('stream')) {
    el.textContent = `last sync ${fmtRelative(store.telemetry.ts)}`;
  }
}, 15000);

boot();

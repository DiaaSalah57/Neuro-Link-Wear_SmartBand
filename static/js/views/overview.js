/**
 * NeuroLink Wear — Live Overview: realtime vitals, IMU motion, live feed,
 * device health and AI insight cards.
 */
import { api } from '../api.js?v=20261001-6';
import { store } from '../store.js?v=20261001-6';
import { onWS } from '../ws.js?v=20261001-6';
import {
  $, $$, esc, icons, toast, fmtTime, fmtRelative, fmtDateTime, fmtNum,
  skeletonCards, emptyState, typeIcon,
} from '../ui.js?v=20261001-6';
import { sparkline } from '../charts.js?v=20261001-6';

let unsubWS = null;
let unsubStore = null;
let feedItems = [];
let historyLoaded = false;

const VITALS = [
  { key: 'heart_rate', label: 'Heart Rate', unit: 'bpm', icon: icons.heart, color: '#241483', soft: 'rgba(36,20,131,.09)', min: 52, max: 112, digits: 0, hiBad: 112, loBad: 52 },
  { key: 'spo2', label: 'Blood Oxygen', unit: '%', icon: icons.lungs, color: '#5b4bd6', soft: 'rgba(91,75,214,.11)', min: 92, max: 100, digits: 0, hiBad: 100, loBad: 92 },
  { key: 'temperature', label: 'Skin Temperature', unit: '°C', icon: icons.thermo, color: '#8f82ee', soft: 'rgba(143,130,238,.13)', min: 35.5, max: 37.8, digits: 1, hiBad: 37.8, loBad: 35.5 },
  { key: 'stress_score', label: 'Stress Index (GSR)', unit: '', icon: icons.wave, color: '#170c5e', soft: 'rgba(23,12,94,.09)', min: 0, max: 1, digits: 2, hiBad: 0.6, loBad: -1 },
];

function statusFor(v, cfg) {
  if (cfg.loBad > -1 && v < cfg.loBad) return 'bad';
  if (v > cfg.hiBad) return 'bad';
  return 'ok';
}

function vitalCard(cfg) {
  return `
  <div class="card vital-card" data-vital="${cfg.key}">
    <div class="card-body">
      <div class="vital-top">
        <div>
          <div class="vital-label">${cfg.label}</div>
          <div class="vital-value" data-v="${cfg.key}">—<span class="unit">${cfg.unit}</span></div>
        </div>
        <div class="vital-icon" style="background:${cfg.soft};color:${cfg.color}">${cfg.icon}</div>
      </div>
      <div data-spark="${cfg.key}"></div>
      <div class="vital-foot">
        <span class="vital-trend flat" data-trend="${cfg.key}">live</span>
        <span class="vital-range">Safe ${cfg.loBad > -1 ? cfg.loBad + '–' : '<'}${cfg.max}${cfg.unit}</span>
      </div>
    </div>
  </div>`;
}

function feedRow(item) {
  const sevClass = item.severity === 'critical' ? 'danger' : item.severity === 'high' ? 'warn' : item.kind === 'ok' ? 'ok' : '';
  return `
    <div class="feed-item">
      <div class="feed-dot ${sevClass}"></div>
      <div class="feed-content">
        <strong style="font-size:calc(13px * var(--fs))">${esc(item.title)}</strong>
        <div class="meta">
          <span>${fmtRelative(item.ts)}</span>
          ${item.badge ? `<span class="badge ${item.severity || 'neutral'}">${esc(item.badge)}</span>` : ''}
          ${item.mlBadge ? `<span class="badge purple ml-tier-badge" data-tier="ml">${esc(item.mlBadge)}</span>` : ''}
        </div>
      </div>
    </div>`;
}

function updateLive(reading) {
  if (!reading || reading.heart_rate === undefined || reading.heart_rate === null) return;
  VITALS.forEach((cfg) => {
    const v = reading[cfg.key];
    const valEl = $(`[data-v="${cfg.key}"]`);
    if (valEl && v !== undefined) {
      const ok = statusFor(v, cfg);
      valEl.innerHTML = `${Number(v).toFixed(cfg.digits)}<span class="unit">${cfg.unit}</span>`;
      valEl.style.color = ok === 'bad' ? 'var(--danger)' : 'var(--text)';
    }
    const spark = store.spark[cfg.key];
    const box = $(`[data-spark="${cfg.key}"]`);
    if (box && spark && spark.length > 3) {
      box.innerHTML = sparkline(spark.slice(-40), { color: cfg.color });
    }
    const trendEl = $(`[data-trend="${cfg.key}"]`);
    if (trendEl && spark && spark.length > 6) {
      const recent = spark.slice(-6);
      const delta = recent[recent.length - 1] - recent[0];
      const cls = Math.abs(delta) < (cfg.max - cfg.min) * 0.03 ? 'flat' : delta > 0 ? 'up' : 'down';
      trendEl.className = `vital-trend ${cls}`;
      trendEl.textContent = cls === 'flat' ? '→ steady' : `${delta > 0 ? '▲' : '▼'} ${Math.abs(delta).toFixed(cfg.digits)}${cfg.unit} / 10s`;
    }
  });

  // IMU
  const actEl = $('#imu-activity');
  if (actEl) {
    const act = reading.activity || 'Resting';
    actEl.innerHTML = `<span class="badge ${act === 'Sleeping' ? 'purple' : act === 'Walking' ? 'ok' : 'neutral'}">${esc(act)}</span>
      <span class="muted" style="margin-left:8px">Motion state from IMU classifier</span>`;
    const acc = Math.min(100, (reading.accel_mag || 0) / 3.5 * 100);
    const gyr = Math.min(100, (reading.gyro_mag || 0) / 3.5 * 100);
    const accBar = $('#imu-accel-bar'), gyrBar = $('#imu-gyro-bar');
    if (accBar) {
      accBar.style.width = `${acc}%`;
      accBar.parentElement.className = `meter ${reading.accel_mag > 2.8 ? 'danger' : reading.accel_mag > 1.2 ? 'warn' : ''}`;
      $('#imu-accel-val').textContent = `${(reading.accel_mag || 0).toFixed(2)} g`;
    }
    if (gyrBar) {
      gyrBar.style.width = `${gyr}%`;
      gyrBar.parentElement.className = `meter ${reading.gyro_mag > 2.4 ? 'danger' : reading.gyro_mag > 1 ? 'warn' : ''}`;
      $('#imu-gyro-val').textContent = `${(reading.gyro_mag || 0).toFixed(2)} rad/s`;
    }
    const st = $('#imu-steps');
    if (st) st.textContent = fmtNum(reading.steps || 0);
  }

  // Live feed — vitals sampled every ~20s to keep it readable
  const now = Date.now();
  if (!feedItems.length || now - feedItems[0].tsAdded > 20000) {
    const item = {
      kind: 'ok', ts: reading.ts, tsAdded: now,
      title: `${reading.activity} · HR ${reading.heart_rate.toFixed(0)} bpm · SpO₂ ${reading.spo2.toFixed(0)}% · stress ${(reading.stress_score || 0).toFixed(2)}`,
    };
    feedItems.unshift(item);
    feedItems = feedItems.slice(0, 30);
    renderFeed();
  }
}

function renderFeed() {
  const box = $('#live-feed');
  if (!box) return;
  if (!feedItems.length) {
    box.innerHTML = emptyState({ icon: icons.activity, title: 'Waiting for sensor data…', body: 'Live readings will appear here as the band streams them.' });
    return;
  }
  box.innerHTML = feedItems.map(feedRow).join('');
}

function pushAlert(alert) {
  const isTier3 = alert.type === 'General Anomaly';
  const mlScore = alert.readings && alert.readings.ml_tier && typeof alert.readings.ml_tier.score === 'number'
    ? ` (${alert.readings.ml_tier.score.toFixed(3)})`
    : '';
  feedItems.unshift({
    kind: 'alert', ts: alert.ts, tsAdded: Date.now(),
    title: alert.title, severity: alert.severity,
    badge: `${alert.type} · ${alert.severity}`,
    mlBadge: isTier3 ? `ML Model · AI-flagged${mlScore}` : '',
  });
  feedItems = feedItems.slice(0, 30);
  renderFeed();
  const badge = $('#nav-alert-count');
  if (badge) {
    const n = (parseInt(badge.textContent, 10) || 0) + 1;
    badge.textContent = n;
    badge.classList.remove('hidden');
  }
  toast('alert', `${alert.type} detected`, alert.title, 9000);
}

export default {
  async render(root) {
    root.innerHTML = `
      <div class="page-head">
        <div>
          <h2>Live Overview</h2>
          <div class="subtitle">Real-time biometrics streaming from the NeuroLink Wear band — updated every 2 seconds.</div>
        </div>
        <div class="page-actions">
          <button class="btn ghost" id="ov-refresh">${icons.refresh}<span>Refresh</span></button>
          <button class="btn soft" id="ov-ai">${icons.robot}<span>Generate AI summary</span></button>
        </div>
      </div>

      <div id="ov-alert-banner"></div>

      <div class="grid cols-4" id="vitals-grid">
        ${skeletonCards(4)}
      </div>

      <div class="grid span-right" style="margin-top:16px">
        <div class="stack">
          <div class="card">
            <div class="card-head">
              <h3>${icons.activity} Motion &amp; IMU Status</h3>
              <span class="sub">accelerometer + gyroscope</span>
            </div>
            <div class="card-body">
              <div id="imu-activity"><div class="skeleton skeleton-line w40"></div></div>
              <div class="imu-grid">
                <div class="imu-cell">
                  <small>Accelerometer</small>
                  <strong id="imu-accel-val">—</strong>
                  <div class="meter"><i id="imu-accel-bar" style="width:0%"></i></div>
                </div>
                <div class="imu-cell">
                  <small>Gyroscope</small>
                  <strong id="imu-gyro-val">—</strong>
                  <div class="meter"><i id="imu-gyro-bar" style="width:0%"></i></div>
                </div>
                <div class="imu-cell">
                  <small>Steps today</small>
                  <strong id="imu-steps">—</strong>
                  <div class="meter"><i style="width:62%"></i></div>
                </div>
              </div>
              <div class="muted" style="font-size:calc(12px * var(--fs))">
                Fall-detection threshold: impact ≥ 2.8 g with rotation ≥ 2.4 rad/s — the band auto-escalates on match.
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-head">
              <h3>${icons.bell} Live Event Feed</h3>
              <span class="row"><span class="live-dot"></span><span class="sub">streaming</span></span>
            </div>
            <div class="card-body">
              <div class="feed" id="live-feed"></div>
            </div>
          </div>
        </div>

        <div class="stack">
          <div class="card">
            <div class="card-head"><h3>${icons.watch} Wearable Device</h3></div>
            <div class="card-body" id="device-card-body">
              <div class="skeleton skeleton-line w80"></div>
              <div class="skeleton skeleton-line w60"></div>
            </div>
          </div>

          <div class="card summary-card">
            <div class="card-head">
              <h3>${icons.robot} NeuroLink AI Insight</h3>
            </div>
            <div class="card-body" id="ai-insight-body">
              <div class="skeleton skeleton-line w80"></div>
              <div class="skeleton skeleton-line"></div>
              <div class="skeleton skeleton-line w60"></div>
            </div>
          </div>

          <div class="card">
            <div class="card-head"><h3>${icons.bolt} Quick Actions</h3></div>
            <div class="card-body" style="display:grid;gap:9px">
              <button class="btn danger block" id="qa-sos">${icons.shield}<span>Trigger emergency SOS</span></button>
              <button class="btn soft block" id="qa-fallcheck">${icons.activity}<span>Fall Detected · "Are you OK?" (30s)</span></button>
              <button class="btn primary block" id="qa-dispatch">${icons.phone}<span>Dispatch emergency contacts</span></button>
              <button class="btn ghost block" id="qa-safety">${icons.map}<span>Open safety &amp; live map</span></button>
              <div class="divider"></div>
              <div class="muted" style="font-size:calc(11.5px * var(--fs));font-weight:600;letter-spacing:.05em;text-transform:uppercase">Demo scenario controls</div>
              <div class="chip-row">
                <button class="chip" data-demo="fall">Simulate fall</button>
                <button class="chip" data-demo="stress">Stress spike</button>
                <button class="chip" data-demo="fever">Fever</button>
                <button class="chip" data-demo="desat">Low SpO₂</button>
              </div>
            </div>
          </div>
        </div>
      </div>`;

    // ── load static data ────────────────────────────────────────────────
    const [latest, summaries] = await Promise.all([
      api.latest().catch(() => null),
      api.summaries(1).catch(() => ({ data: [] })),
    ]);

    // Seed sparkline buffers once
    if (!historyLoaded) {
      try {
        const hist = await api.history(2, 80);
        hist.data.forEach((p) => store.pushSpark(p));
        historyLoaded = true;
      } catch { /* fine */ }
    }

    $('#vitals-grid').innerHTML = VITALS.map(vitalCard).join('');
    if (latest) updateLive(latest);

    // Device card
    const dev = latest && latest.device;
    $('#device-card-body').innerHTML = dev ? `
      <div class="row" style="align-items:flex-start">
        <div class="vital-icon" style="background:var(--accent-soft);color:var(--accent)">${icons.watch}</div>
        <div style="flex:1;min-width:0">
          <strong style="display:block">${esc(dev.name)}</strong>
          <small class="muted">${esc(dev.model)} · SN ${esc(dev.serial)} · FW ${esc(dev.firmware)}</small>
        </div>
        <span class="badge ${dev.online ? 'ok' : 'high'}">${dev.online ? 'Online' : 'Offline'}</span>
      </div>
      <div class="divider"></div>
      <div class="flex-between"><span class="muted">Battery</span><b class="mono">${dev.battery}%${dev.charging ? ' ⚡' : ''}</b></div>
      <div class="meter" style="margin:6px 0 12px"><i style="width:${dev.battery}%;background:${dev.battery < 20 ? 'var(--danger)' : 'var(--ok)'}"></i></div>
      <div class="flex-between"><span class="muted">Last sync</span><b>${fmtRelative(dev.last_seen)}</b></div>
    ` : emptyState({ icon: icons.watch, title: 'No device paired', body: 'Pair a NeuroLink band in Care Team → Devices.' });

    // AI insight
    const s = summaries.data && summaries.data[0];
    $('#ai-insight-body').innerHTML = s ? `
      <div class="row" style="align-items:center;margin-bottom:10px">
        <div class="summary-score" style="--score:${Math.round((s.score || 0.8) * 100)}">
          <span>${Math.round((s.score || 0.8) * 100)}</span>
        </div>
        <div>
          <strong style="display:block;font-size:calc(13.5px * var(--fs))">${esc(s.title)}</strong>
          <small class="muted">${fmtDateTime(s.ts)} · wellbeing score</small>
        </div>
      </div>
      <p style="font-size:calc(12.8px * var(--fs));line-height:1.65;color:var(--text-2)">${esc(s.body.length > 330 ? s.body.slice(0, 330) + '…' : s.body)}</p>
      <div>${(s.tags || []).map((t) => `<span class="tag-pill">${esc(t)}</span>`).join('')}</div>
      <button class="btn ghost sm" id="ai-more" style="margin-top:10px">${icons.robot} Read full analysis</button>
    ` : emptyState({ icon: icons.robot, title: 'No AI summaries yet', body: 'Generate one from the button above.' });

    // ── events ──────────────────────────────────────────────────────────
    $('#ov-refresh').onclick = async () => {
      const r = await api.latest().catch(() => null);
      if (r && r.heart_rate !== undefined && r.heart_rate !== null) {
        store.pushSpark(r);
        updateLive(r);
        toast('info', 'Telemetry refreshed', `Latest reading at ${fmtTime(r.ts)}`);
      } else {
        toast('info', 'Waiting for wearable data', 'No readings received from the band yet.');
      }
    };
    $('#ov-ai').onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        const s2 = await api.generateSummary();
        toast('success', 'AI summary generated', 'Fresh analysis added to the insights feed.');
        $('#ai-insight-body').innerHTML = `
          <div class="row" style="align-items:center;margin-bottom:10px">
            <div class="summary-score" style="--score:${Math.round((s2.score || 0.8) * 100)}"><span>${Math.round((s2.score || 0.8) * 100)}</span></div>
            <div><strong style="display:block;font-size:calc(13.5px * var(--fs))">${esc(s2.title)}</strong><small class="muted">just now · wellbeing score</small></div>
          </div>
          <p style="font-size:calc(12.8px * var(--fs));line-height:1.65;color:var(--text-2)">${esc(s2.body)}</p>
          <div>${(s2.tags || []).map((t) => `<span class="tag-pill">${esc(t)}</span>`).join('')}</div>`;
      } catch (err) {
        toast('error', 'Could not generate summary', err.message);
      } finally {
        btn.disabled = false;
      }
    };
    $('#qa-sos').onclick = () => window.dispatchEvent(new CustomEvent('nlw:sos'));
    $('#qa-fallcheck').onclick = () => window.dispatchEvent(new CustomEvent('nlw:fallcheck'));
    $('#qa-dispatch').onclick = () => { location.hash = '#/safety?dispatch=1'; };
    $('#qa-safety').onclick = () => { location.hash = '#/safety'; };
    $$('[data-demo]').forEach((btn) => {
      btn.onclick = async () => {
        try {
          await api.demoTrigger(btn.dataset.demo);
          toast('info', 'Scenario triggered', `Simulator is now producing a "${btn.dataset.demo}" pattern — watch the feed.`);
        } catch (err) {
          toast('error', 'Trigger failed', err.message);
        }
      };
    });
    const moreBtn = $('#ai-more');
    if (moreBtn) moreBtn.onclick = () => { location.hash = '#/alerts?tab=insights'; };

    renderFeed();

    // ── live subscriptions ──────────────────────────────────────────────
    unsubWS = onWS((msg) => {
      if (msg.type === 'telemetry') {
        store.pushSpark(msg.data);
        updateLive(msg.data);
      } else if (msg.type === 'alert' && msg.data) {
        pushAlert(msg.data);
      }
    });
    unsubStore = store.subscribe((what) => {
      if (what === 'telemetry' && store.telemetry) updateLive(store.telemetry);
    });

    // Show active-alerts banner if any
    try {
      const sum = await api.alertsSummary();
      if (!$('#ov-alert-banner')) return;
      const active = sum.by_status.active || 0;
      store.set('activeAlerts', active);
      if (active > 0) {
        $('#ov-alert-banner').innerHTML = `
          <div class="notif-banner danger" style="margin-bottom:16px">
            <div class="nb-body">
              <strong>${active} active alert${active > 1 ? 's' : ''} need${active > 1 ? '' : 's'} attention</strong>
              <div class="muted" style="font-size:calc(12.5px * var(--fs))">Open AI Alerts to review explanations and take action.</div>
            </div>
            <button class="btn danger sm" onclick="location.hash='#/alerts'">Review</button>
          </div>`;
      }
    } catch { /* non-fatal */ }
  },

  destroy() {
    if (unsubWS) { unsubWS(); unsubWS = null; }
    if (unsubStore) { unsubStore(); unsubStore = null; }
    feedItems = [];
  },
};

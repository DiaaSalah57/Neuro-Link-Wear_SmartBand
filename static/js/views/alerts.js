/**
 * NeuroLink Wear — AI Insights & Alerts: anomaly alerts with severity badges,
 * LLM plain-language explanations, recommendations, plus the AI summary feed.
 */
import { api } from '../api.js?v=20261001-8';
import { onWS } from '../ws.js?v=20261001-8';
import {
  $, $$, esc, icons, toast, fmtDateTime, fmtRelative, emptyState,
  typeIcon, skeletonCards, confirmDialog,
} from '../ui.js?v=20261001-8';

let unsubWS = null;
let state = { status: 'all', severity: 'all', type: 'all' };

function alertCard(a) {
  const recs = (a.recommendation || '').split('•').map((s) => s.trim()).filter(Boolean);
  const r = a.readings || {};
  const isTier3 = a.type === 'General Anomaly';
  const mlTier = r.ml_tier && typeof r.ml_tier === 'object' ? r.ml_tier : null;
  const hasMlScore = mlTier && mlTier.available && typeof mlTier.score === 'number';

  const pills = [];
  if (r.heart_rate) pills.push(['HR', `${Number(r.heart_rate).toFixed(0)} bpm`]);
  if (r.spo2) pills.push(['SpO₂', `${Number(r.spo2).toFixed(0)}%`]);
  if (r.temperature) pills.push(['Temp', `${Number(r.temperature).toFixed(1)} °C`]);
  if (r.gsr !== undefined) pills.push(['GSR', `${Number(r.gsr).toFixed(2)} µS`]);
  if (r.hrv) pills.push(['HRV', `${Number(r.hrv).toFixed(0)} ms`]);
  if (r.stress !== undefined) pills.push(['Stress', Number(r.stress).toFixed(2)]);
  if (r.accel_mag) pills.push(['Impact', `${Number(r.accel_mag).toFixed(1)} g`]);
  if (hasMlScore && isTier3) pills.push(['ML Score', Number(mlTier.score).toFixed(3)]);

  // Equation terms & Tier 3 ML model score breakdown for the expanded detail view
  const eqTerms = [];
  if (r.stress_z_max !== undefined) eqTerms.push(['Peak σ-evidence', `${Number(r.stress_z_max).toFixed(2)}σ`]);
  if (r.stress_terms && r.stress_terms.gsr_phasic_z !== undefined) eqTerms.push(['z(GSR phasic)', `${Number(r.stress_terms.gsr_phasic_z).toFixed(2)}σ`]);
  if (r.stress_terms && r.stress_terms.hrv_drop_z !== undefined) eqTerms.push(['z(HRV drop)', `${Number(r.stress_terms.hrv_drop_z).toFixed(2)}σ`]);
  if (r.core_temp !== undefined) eqTerms.push(['Core-equiv temp', `${Number(r.core_temp).toFixed(2)} °C`]);
  if (r.hypoxic_burden !== undefined && Number(r.hypoxic_burden) > 0) eqTerms.push(['Hypoxic burden', `${Number(r.hypoxic_burden).toFixed(1)} %·min`]);
  if (hasMlScore) eqTerms.push(['Isolation Forest score', Number(mlTier.score).toFixed(4)]);

  return `
  <div class="card alert-card sev-${a.severity} ${isTier3 ? 'tier-ml-card' : ''}" data-alert-id="${a.id}" data-alert-type="${esc(a.type)}">
    <div class="card-pad">
      <div class="alert-head">
        <div>
          <div class="row" style="gap:8px">
            <span class="vital-icon" style="width:32px;height:32px;font-size:calc(15px * var(--fs));background:${isTier3 ? 'var(--accent-soft)' : 'var(--danger-soft)'};color:${isTier3 ? 'var(--accent)' : 'var(--danger)'}">${isTier3 ? icons.robot : typeIcon(a.type)}</span>
            <h4>${esc(a.title)}</h4>
          </div>
          <div class="alert-meta">
            <span class="badge ${a.severity}">${esc(a.severity)}</span>
            ${isTier3 ? `<span class="badge purple ml-tier-badge" data-tier="ml" title="Flagged by Tier 3 Isolation Forest ML model">${icons.robot} ML Model · AI-flagged</span>` : ''}
            <span class="badge ${a.status}">${esc(a.status)}</span>
            <span>${esc(a.type)}</span>
            <span>·</span>
            <span title="${fmtDateTime(a.ts)}">${fmtRelative(a.ts)}</span>
            ${a.created_by && a.created_by !== 'system' ? `<span class="badge purple">${esc(a.created_by)}</span>` : ''}
          </div>
        </div>
      </div>

      <div class="ai-explain">
        <div class="ai-tag"><span style="display:inline-flex;width:15px;height:15px;flex:0 0 15px">${icons.robot}</span> <span>${isTier3 ? 'Tier 3 ML model explanation' : 'AI explanation'}</span></div>
        ${esc(a.explanation)}
      </div>

      ${recs.length ? `
      <div class="recommend-list">
        <div class="ai-tag" style="display:flex;align-items:center;gap:6px;color:var(--ok);margin-bottom:8px;font-weight:800;font-size:calc(13px * var(--fs));letter-spacing:.06em;text-transform:uppercase">
          <span style="display:inline-flex;width:15px;height:15px;flex:0 0 15px">${icons.shield}</span>
          <strong style="font-weight:800">Recommended actions</strong>
        </div>
        <ul style="list-style:disc;padding-left:18px;font-weight:600">
          ${recs.map((x) => `<li style="font-weight:600">${esc(x)}</li>`).join('')}
        </ul>
      </div>` : ''}

      ${pills.length ? `
      <div class="readings-strip">
        ${pills.map(([k, v]) => `<span class="reading-pill">${k} <b>${v}</b></span>`).join('')}
      </div>` : ''}

      ${(isTier3 || hasMlScore) && eqTerms.length ? `
      <div class="readings-strip ml-detail-strip" data-ml-detail="1" style="margin-top:8px">
        <span class="reading-pill" style="border-color:rgba(91,75,214,.32);background:var(--accent-soft);color:var(--accent)"><b>${isTier3 ? 'Tier 3 · ML Model' : 'Ensemble Evidence'}</b></span>
        ${eqTerms.map(([k, v]) => `<span class="reading-pill">${esc(k)} <b class="mono">${esc(v)}</b></span>`).join('')}
      </div>` : ''}

      <div class="alert-actions">
        ${a.type === 'Fall Detected' && a.status !== 'resolved' ? `<button class="btn soft sm" data-act="fallcheck">${icons.activity} Are you OK? (30s check)</button>` : ''}
        ${a.status === 'active' ? `<button class="btn warn sm" data-act="ack">${icons.check} Acknowledge</button>` : ''}
        ${a.status !== 'resolved' ? `<button class="btn primary sm" data-act="resolve">${icons.check} Mark resolved</button>` : ''}
        <button class="btn ghost sm" data-act="dispatch">${icons.phone} Dispatch contacts</button>
        ${a.lat ? `<button class="btn ghost sm" data-act="map">${icons.pin} View on map</button>` : ''}
        ${a.status === 'resolved' && a.resolved_by ? `<span class="muted" style="font-size:calc(11.5px * var(--fs));align-self:center">resolved by ${esc(a.resolved_by)} · ${fmtRelative(a.resolved_at)}</span>` : ''}
      </div>
    </div>
  </div>`;
}

function summaryCard(s) {
  return `
  <div class="card summary-card" style="margin-bottom:12px">
    <div class="card-pad">
      <div class="row" style="align-items:flex-start;gap:12px">
        <div class="summary-score" style="--score:${Math.round((s.score || 0.8) * 100)}">
          <span>${Math.round((s.score || 0.8) * 100)}</span>
        </div>
        <div style="flex:1;min-width:0">
          <div class="flex-between">
            <strong style="font-size:calc(13.6px * var(--fs))">${esc(s.title)}</strong>
            <span class="badge ${s.period === 'weekly' ? 'purple' : s.period === 'event' ? 'high' : 'neutral'}">${esc(s.period)}</span>
          </div>
          <small class="muted">${fmtDateTime(s.ts)}</small>
          <p style="font-size:calc(12.8px * var(--fs));line-height:1.65;color:var(--text-2);margin-top:8px">${esc(s.body)}</p>
          <div>${(s.tags || []).map((t) => `<span class="tag-pill">${esc(t)}</span>`).join('')}</div>
        </div>
      </div>
    </div>
  </div>`;
}

async function loadAlerts() {
  const box = $('#alerts-list');
  if (!box) return;
  box.innerHTML = `<div class="grid" style="gap:12px">
    <div class="skeleton skeleton-card" style="height:190px"></div>
    <div class="skeleton skeleton-card" style="height:190px"></div>
  </div>`;
  const data = await api.alerts({
    status: state.status, severity: state.severity, type: state.type, hours: 24 * 14, limit: 60,
  });
  if (!data.data.length) {
    const filtersOn = state.status !== 'all' || state.severity !== 'all' || state.type !== 'all';
    box.innerHTML = filtersOn
      ? emptyState({
        icon: icons.inbox, title: 'No alerts match these filters',
        body: 'Try widening the date range or clearing the status / severity filters.',
        action: '<button class="btn ghost sm" id="clear-filters">Clear filters</button>',
      })
      : emptyState({
        icon: icons.shield, title: 'No incidents recorded',
        body: 'NeuroLink AI is watching every reading. The moment a stress spike, fever, low-oxygen episode or fall is detected, it will appear here with a full explanation.',
      });
    const cf = $('#clear-filters');
    if (cf) cf.onclick = () => {
      state = { status: 'all', severity: 'all', type: 'all' };
      $$('.chip-row .chip').forEach((c) => c.classList.remove('active'));
      $(`[data-filter="status"][data-value="all"]`)?.classList.add('active');
      loadAlerts().catch(() => {});
    };
    return;
  }
  box.innerHTML = `<div class="grid" style="gap:14px">${data.data.map(alertCard).join('')}</div>`;

  $$('[data-alert-id] [data-act]').forEach((btn) => {
    btn.onclick = async () => {
      const card = btn.closest('[data-alert-id]');
      const id = +card.dataset.alertId;
      const alert = data.data.find((x) => x.id === id);
      const act = btn.dataset.act;
      try {
        if (act === 'fallcheck') {
          window.dispatchEvent(new CustomEvent('nlw:fallcheck', { detail: alert }));
        } else if (act === 'ack') {
          btn.disabled = true;
          await api.acknowledgeAlert(id);
          toast('success', 'Alert acknowledged', 'Your name is now attached to the incident timeline.');
          loadAlerts().catch(() => {});
        } else if (act === 'resolve') {
          if (await confirmDialog('Resolve this alert?', 'This marks the incident as handled and moves it out of the active queue.', 'Mark resolved')) {
            await api.resolveAlert(id);
            toast('success', 'Alert resolved', 'Moved to the resolved incidents log.');
            loadAlerts().catch(() => {});
          }
        } else if (act === 'dispatch') {
          sessionStorage.setItem('nlw_dispatch_alert', JSON.stringify({ id, title: alert.title }));
          location.hash = '#/safety?dispatch=1';
        } else if (act === 'map') {
          sessionStorage.setItem('nlw_map_focus', JSON.stringify({ lat: alert.lat, lng: alert.lng, label: alert.title, ts: alert.ts }));
          location.hash = '#/safety';
        }
      } catch (err) {
        toast('error', 'Action failed', err.message);
        btn.disabled = false;
      }
    };
  });
}

export default {
  async render(root, ctx) {
    const params = ctx.params || {};
    if (params.tab === 'insights') state.tab = 'insights';
    root.innerHTML = `
      <div class="page-head">
        <div>
          <h2>AI Insights &amp; Alerts</h2>
          <div class="subtitle">Every anomaly is detected in real time and explained in plain language by NeuroLink AI, with concrete next steps for the care team.</div>
        </div>
        <div class="page-actions">
          <button class="btn ghost" id="alerts-refresh">${icons.refresh}<span>Refresh</span></button>
          <button class="btn soft" id="alerts-generate">${icons.robot}<span>New AI summary</span></button>
        </div>
      </div>

      <div class="tabs" id="alerts-tabs">
        <button class="tab-btn ${state.tab !== 'insights' ? 'active' : ''}" data-tab="incidents">Incident alerts</button>
        <button class="tab-btn ${state.tab === 'insights' ? 'active' : ''}" data-tab="insights">AI health summaries</button>
      </div>

      <div id="tab-incidents" class="${state.tab === 'insights' ? 'hidden' : ''}">
        <div class="row" style="margin-bottom:16px;justify-content:space-between">
          <div class="chip-row" id="filter-row">
            <button class="chip active" data-filter="status" data-value="all">All</button>
            <button class="chip" data-filter="status" data-value="active">Active</button>
            <button class="chip" data-filter="status" data-value="acknowledged">Acknowledged</button>
            <button class="chip" data-filter="status" data-value="resolved">Resolved</button>
            <span style="width:12px"></span>
            <button class="chip" data-filter="severity" data-value="critical">Critical</button>
            <button class="chip" data-filter="severity" data-value="high">High</button>
            <button class="chip" data-filter="severity" data-value="medium">Medium</button>
          </div>
        </div>
        <div id="alerts-list"></div>
      </div>

      <div id="tab-insights" class="${state.tab === 'insights' ? '' : 'hidden'}">
        <div class="grid span-right">
          <div id="summaries-list"></div>
          <div class="stack">
            <div class="card">
              <div class="card-head"><h3>${icons.robot} How NeuroLink AI works</h3></div>
              <div class="card-body" style="font-size:calc(12.8px * var(--fs));line-height:1.7;color:var(--text-2)">
                <p><b>1 · Detect.</b> An ensemble of threshold rules, an Isolation Forest and an LSTM autoencoder watch every reading for anomalies in stress, temperature, oxygen and motion.</p>
                <p style="margin-top:8px"><b>2 · Explain.</b> Each detection is turned into a plain-language explanation referencing the exact sensor values — no jargon.</p>
                <p style="margin-top:8px"><b>3 · Advise.</b> Actionable recommendations are attached to every incident, and daily summaries track the bigger picture.</p>
                <div class="divider"></div>
                <div class="muted">Summaries refresh on demand and after major incidents.</div>
              </div>
            </div>
          </div>
        </div>
      </div>`;

    // tabs
    $$('#alerts-tabs .tab-btn').forEach((b) => {
      b.onclick = () => {
        state.tab = b.dataset.tab;
        $$('#alerts-tabs .tab-btn').forEach((x) => x.classList.toggle('active', x === b));
        $('#tab-incidents').classList.toggle('hidden', state.tab !== 'incidents');
        $('#tab-insights').classList.toggle('hidden', state.tab !== 'insights');
        if (state.tab === 'insights') loadSummaries();
      };
    });

    // filters
    $$('#filter-row .chip').forEach((chip) => {
      chip.onclick = () => {
        const f = chip.dataset.filter;
        const siblings = $$(`#filter-row [data-filter="${f}"]`);
        // severity filter is toggleable
        if (f === 'severity') {
          const turningOff = chip.classList.contains('active');
          siblings.forEach((c) => c.classList.remove('active'));
          if (turningOff) {
            state.severity = 'all';
            $('#filter-row [data-filter="status"][data-value="all"]')?.classList.add('active');
          } else {
            chip.classList.add('active');
            state.severity = chip.dataset.value;
          }
        } else {
          siblings.forEach((c) => c.classList.remove('active'));
          chip.classList.add('active');
          state.status = chip.dataset.value;
        }
        loadAlerts().catch(() => {});
      };
    });

    $('#alerts-refresh').onclick = () => loadAlerts().catch(() => {});
    $('#alerts-generate').onclick = async () => {
      const genBtn = $('#alerts-generate');
      genBtn.disabled = true;
      try {
        await api.generateSummary();
        toast('success', 'AI summary ready', 'A fresh analysis was added to the summaries tab.');
        state.tab = 'insights';
        $$('#alerts-tabs .tab-btn').forEach((x) => x.classList.toggle('active', x.dataset.tab === 'insights'));
        $('#tab-incidents').classList.add('hidden');
        $('#tab-insights').classList.remove('hidden');
        loadSummaries();
      } catch (err) {
        toast('error', 'Generation failed', err.message);
      } finally {
        genBtn.disabled = false;
      }
    };

    async function loadSummaries() {
      const box = $('#summaries-list');
      if (!box) return;
      box.innerHTML = skeletonCards(1);
      try {
        const res = await api.summaries(12);
        box.innerHTML = res.data.length
          ? res.data.map(summaryCard).join('')
          : emptyState({ icon: icons.robot, title: 'No AI summaries yet', body: 'Click “New AI summary” to compose one from the last 24 hours of readings.' });
      } catch (err) {
        box.innerHTML = emptyState({ icon: icons.alert, title: 'Could not load summaries', body: esc(err.message) });
      }
    }

    await loadAlerts();
    if (state.tab === 'insights') loadSummaries();

    unsubWS = onWS((msg) => {
      if (msg.type === 'alert' && msg.data && state.status === 'active') loadAlerts().catch(() => {});
    });
  },
  destroy() {
    if (unsubWS) { unsubWS(); unsubWS = null; }
    state = { status: 'all', severity: 'all', type: 'all' };
  },
};

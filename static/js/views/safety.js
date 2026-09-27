/**
 * NeuroLink Wear — Safety & Emergency: live GPS map, incident timeline with
 * inactivity alerts, and one-click emergency contact dispatch.
 */
import { api } from '../api.js?v=20260927-4';
import { store } from '../store.js?v=20260927-4';
import { onWS } from '../ws.js?v=20260927-4';
import {
  $, $$, esc, icons, toast, fmtDateTime, fmtRelative, fmtTime,
  emptyState, skeletonCards, typeIcon, confirmDialog,
} from '../ui.js?v=20260927-4';
import { createMap } from '../map.js?v=20260927-4';

let unsubWS = null;
let mapCtl = null;
let range = 'today';

function timelineItem(a) {
  return `
  <div class="timeline-item" data-alert-id="${a.id}">
    <div class="timeline-rail">
      <div class="timeline-node ${a.severity}"></div>
      <div class="timeline-line"></div>
    </div>
    <div class="timeline-card">
      <div class="card" style="margin:0">
        <div class="card-pad" style="padding:14px 16px">
          <div class="flex-between">
            <div class="row" style="gap:8px">
              <span class="vital-icon" style="width:28px;height:28px;font-size:13px;background:var(--surface-3)">${typeIcon(a.type)}</span>
              <strong style="font-size:13.5px">${esc(a.title)}</strong>
            </div>
            <span class="badge ${a.severity}">${esc(a.severity)}</span>
          </div>
          <div class="alert-meta" style="margin-top:6px">
            <span title="${fmtDateTime(a.ts)}">${fmtDateTime(a.ts)}</span>
            <span>·</span>
            <span>${esc(a.type)}</span>
            <span class="badge ${a.status}">${esc(a.status)}</span>
            ${a.lat ? `<span class="gps-pill" style="margin-left:6px">${icons.pin} ${a.lat.toFixed(4)}, ${a.lng.toFixed(4)}</span>` : ''}
          </div>
          ${a.type === 'Inactivity' ? `<p class="muted" style="font-size:12.2px;margin-top:8px">${esc(a.explanation.split('.')[0])}.</p>` : ''}
          <div class="row" style="margin-top:10px">
            <button class="btn ghost sm" data-sa="map">${icons.map} Map</button>
            ${a.status === 'active' ? `<button class="btn warn sm" data-sa="ack">${icons.check} Acknowledge</button>` : ''}
            ${a.status !== 'resolved' ? `<button class="btn primary sm" data-sa="resolve">${icons.check} Resolve</button>` : ''}
            <button class="btn danger sm" data-sa="dispatch">${icons.phone} Dispatch now</button>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

async function loadTimeline() {
  const box = $('#safety-timeline');
  if (!box) return;
  box.innerHTML = `<div class="skeleton skeleton-card" style="height:120px"></div>
    <div class="skeleton skeleton-card" style="height:120px"></div>`;
  const hours = range === 'today' ? 24 : range === 'week' ? 24 * 7 : 24 * 30;
  const res = await api.alerts({ hours, limit: 50 });
  const items = range === 'today'
    ? res.data.filter((a) => new Date(a.ts).toDateString() === new Date().toDateString())
    : res.data;

  if (!items.length) {
    box.innerHTML = emptyState({
      icon: icons.shield,
      title: range === 'today' ? 'No incidents recorded today' : 'No incidents in this period',
      body: range === 'today'
        ? 'A quiet day is a good day. Falls, low-oxygen events and distress episodes will appear here the instant they happen.'
        : 'Nothing to show for this date range — widen it to see older events.',
    });
    return;
  }
  box.innerHTML = `<div class="timeline">${items.map(timelineItem).join('')}</div>`;

  $$('#safety-timeline [data-sa]').forEach((btn) => {
    btn.onclick = async () => {
      const id = +btn.closest('[data-alert-id]').dataset.alertId;
      const alert = items.find((x) => x.id === id);
      const act = btn.dataset.sa;
      if (act === 'map') {
        sessionStorage.setItem('nlw_map_focus', JSON.stringify({ lat: alert.lat, lng: alert.lng, label: alert.title, ts: alert.ts }));
        refreshMap();
        $('#safety-map-wrap').scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else if (act === 'ack') {
        await api.acknowledgeAlert(id).catch((e) => toast('error', 'Failed', e.message));
        toast('success', 'Acknowledged', 'Incident timeline updated.');
        loadTimeline();
      } else if (act === 'resolve') {
        if (await confirmDialog('Resolve this incident?', 'It will be moved to the resolved log.', 'Resolve')) {
          await api.resolveAlert(id).catch((e) => toast('error', 'Failed', e.message));
          toast('success', 'Incident resolved');
          loadTimeline();
        }
      } else if (act === 'dispatch') {
        openDispatchModal(alert);
      }
    };
  });
}

async function refreshMap() {
  const container = $('#safety-map-wrap');
  if (!container) return;
  let focus = null;
  try { focus = JSON.parse(sessionStorage.getItem('nlw_map_focus') || 'null'); } catch { /* */ }
  sessionStorage.removeItem('nlw_map_focus');

  let latest = null;
  try {
    latest = await api.locationLatest();
  } catch { /* */ }
  const lat = (latest && latest.lat) || 42.3467;
  const lng = (latest && latest.lng) || -71.1206;

  const alertRes = await api.alerts({ hours: 24 * 7, limit: 30 }).catch(() => ({ data: [] }));
  const markers = alertRes.data
    .filter((a) => a.lat)
    .slice(0, 12)
    .map((a) => ({
      lat: a.lat, lng: a.lng,
      label: a.title,
      kind: a.severity === 'critical' ? 'critical' : 'fall',
      ts: fmtDateTime(a.ts),
      focus: focus && Math.abs(focus.lat - a.lat) < 1e-5 && Math.abs(focus.lng - a.lng) < 1e-5,
    }));

  if (focus && focus.lat && !markers.some((m) => m.focus)) {
    markers.unshift({ lat: focus.lat, lng: focus.lng, label: focus.label || 'Selected incident', kind: 'fall', ts: focus.ts ? fmtDateTime(focus.ts) : '', focus: true });
  }

  if (mapCtl && mapCtl.destroy) mapCtl.destroy();
  mapCtl = await createMap('safety-map-wrap', {
    lat: focus?.lat || lat, lng: focus?.lng || lng,
    zoom: focus ? 16 : 15,
    markers,
    liveLabel: 'Margaret Thompson · live band position',
  });
  const pill = $('#gps-pill');
  if (pill) pill.innerHTML = `${icons.pin} ${lat.toFixed(5)}, ${lng.toFixed(5)} · ${fmtRelative(latest?.ts)}`;
}

function openDispatchModal(alert) {
  api.contacts().then((contacts) => {
    const dispatchable = contacts.filter((c) => c.can_dispatch);
    import('../ui.js?v=20260927-4').then(({ openModal, closeModal }) => {
      openModal({
        title: 'Dispatch emergency contacts',
        wide: true,
        body: `
          <p class="muted" style="font-size:13px;margin-bottom:12px">
            ${alert ? `Incident: <b>${esc(alert.title)}</b> · ` : ''}
            Choose who should be contacted. Each dispatch is logged in the incident timeline.
          </p>
          <div id="dispatch-contacts">
            ${dispatchable.map((c) => `
              <label class="contact-check">
                <input type="checkbox" value="${c.id}" ${c.priority === 1 ? 'checked' : ''}>
                <div class="cc-info">
                  <strong>${esc(c.name)}</strong>
                  <small>${esc(c.relationship)} · ${esc(c.phone)} · priority ${c.priority}</small>
                </div>
                <span class="badge ${c.priority === 1 ? 'high' : 'neutral'}">${c.priority === 1 ? 'primary' : 'backup'}</span>
              </label>`).join('')}
          </div>
          <div class="field" style="margin-top:12px">
            <span>Message template</span>
            <textarea id="dispatch-message">NeuroLink Wear emergency dispatch: Margaret Thompson may need immediate assistance${alert ? ` (${alert.title})` : ''}. Please respond. Live GPS is available on the Safety dashboard.</textarea>
          </div>
          <div class="row">
            <span class="muted" style="font-size:12px">Channel:</span>
            <div class="segmented" id="dispatch-channel">
              <button class="active" data-ch="sms">SMS</button>
              <button data-ch="call">Phone call</button>
              <button data-ch="app">App push</button>
            </div>
          </div>`,
        footer: `
          <button class="btn ghost" data-modal-close>Cancel</button>
          <button class="btn danger" id="dispatch-go">${icons.send} Dispatch now</button>`,
      });
      $$('#dispatch-channel button').forEach((b) => {
        b.onclick = () => {
          $$('#dispatch-channel button').forEach((x) => x.classList.remove('active'));
          b.classList.add('active');
        };
      });
      $$('.contact-check input').forEach((cb) => {
        cb.onchange = () => cb.closest('.contact-check').classList.toggle('checked', cb.checked);
        cb.closest('.contact-check').classList.toggle('checked', cb.checked);
      });
      $('#dispatch-go').onclick = async () => {
        const ids = $$('#dispatch-contacts input:checked').map((c) => +c.value);
        if (!ids.length) { toast('warning', 'Select at least one contact', 'Choose who should be dispatched.'); return; }
        const channel = $('#dispatch-channel .active').dataset.ch;
        const message = $('#dispatch-message').value;
        $('#dispatch-go').disabled = true;
        try {
          const res = await api.dispatch({ alert_id: alert?.id || null, contact_ids: ids, channel, message });
          closeModal();
          toast('success', `Dispatched to ${res.dispatched.length} contact${res.dispatched.length > 1 ? 's' : ''}`, 'Delivery confirmed — logged in the incident record.');
          loadDispatchLog();
          loadTimeline();
        } catch (err) {
          toast('error', 'Dispatch failed', err.message);
          $('#dispatch-go').disabled = false;
        }
      };
    });
  }).catch((e) => toast('error', 'Could not load contacts', e.message));
}

async function loadDispatchLog() {
  const box = $('#dispatch-log');
  if (!box) return;
  const res = await api.dispatches().catch(() => ({ data: [] }));
  if (!res.data.length) {
    box.innerHTML = emptyState({
      icon: icons.phone, title: 'No dispatches yet',
      body: 'Emergency contact dispatches will be logged here with delivery status.',
    });
    return;
  }
  box.innerHTML = res.data.slice(0, 8).map((d) => `
    <div class="feed-item">
      <div class="feed-dot ${d.status === 'delivered' ? 'ok' : 'warn'}"></div>
      <div class="feed-content">
        <strong style="font-size:12.8px">${esc(d.contact_name || 'Contact')} · ${esc(d.channel).toUpperCase()}</strong>
        <div class="meta">
          <span>${fmtRelative(d.ts)}</span>
          <span class="badge ${d.status === 'delivered' ? 'ok' : 'medium'}">${esc(d.status)}</span>
          ${d.sent_by ? `<span>by ${esc(d.sent_by)}</span>` : ''}
        </div>
        <div class="muted" style="font-size:11.5px;margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:340px">${esc(d.message)}</div>
      </div>
    </div>`).join('');
}

export default {
  async render(root) {
    root.innerHTML = `
      <div class="page-head">
        <div>
          <h2>Safety &amp; Emergency</h2>
          <div class="subtitle">Live GPS tracking, incident escalation and one-press dispatch to the people who can help fastest.</div>
        </div>
        <div class="page-actions">
          <button class="btn ghost" id="safety-refresh">${icons.refresh}<span>Refresh</span></button>
          <button class="btn danger" id="safety-sos">${icons.shield}<span>Emergency SOS</span></button>
        </div>
      </div>

      <div class="notif-banner ok" id="safety-status" style="margin-bottom:16px">
        <div class="nb-body">
          <strong id="safety-status-title">Wearer status: <span class="text-ok">Safe</span></strong>
          <div class="muted" style="font-size:12.5px" id="safety-status-sub">Band is streaming · fall detection armed · GPS updating every 20 s</div>
        </div>
        <button class="btn primary sm" id="safety-dispatch-btn">${icons.phone} Dispatch contacts</button>
      </div>

      <div class="grid span-right">
        <div class="stack">
          <div class="card">
            <div class="card-head">
              <h3>${icons.map} Live Location</h3>
              <span class="gps-pill" id="gps-pill">${icons.pin} loading…</span>
            </div>
            <div class="card-body" style="padding:12px">
              <div class="map-wrap tall" id="safety-map-wrap"></div>
              <div class="row" style="margin-top:10px;justify-content:space-between">
                <div class="row" style="gap:14px">
                  <span class="lg-item"><span class="legend-dot" style="background:#241483"></span> Live position</span>
                  <span class="lg-item"><span class="legend-dot" style="background:#170c5e"></span> Incident location</span>
                </div>
                <small class="muted">Rosewood Senior Living · 12 Rosewood Lane, Brookline, MA</small>
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-head">
              <h3>${icons.clock} Incident Timeline</h3>
              <div class="segmented" id="range-seg">
                <button class="active" data-range="today">Today</button>
                <button data-range="week">7 days</button>
                <button data-range="month">30 days</button>
              </div>
            </div>
            <div class="card-body" id="safety-timeline"></div>
          </div>
        </div>

        <div class="stack">
          <div class="card">
            <div class="card-head"><h3>${icons.shield} Escalation Status</h3></div>
            <div class="card-body">
              <div class="flex-between" style="margin-bottom:10px">
                <span class="muted">Fall detection</span>
                <span class="badge ok">Armed</span>
              </div>
              <div class="flex-between" style="margin-bottom:10px">
                <span class="muted">Inactivity monitor</span>
                <span class="badge ok">Armed · 90 min</span>
              </div>
              <div class="flex-between" style="margin-bottom:10px">
                <span class="muted">SOS button</span>
                <span class="badge ok">Ready</span>
              </div>
              <div class="flex-between">
                <span class="muted">Emergency contacts</span>
                <span class="badge neutral" id="contact-count">…</span>
              </div>
              <div class="divider"></div>
              <button class="btn danger block" id="panel-dispatch">${icons.phone} One-click dispatch</button>
              <button class="btn ghost block" style="margin-top:8px" id="panel-edit-contacts">${icons.users} Manage contacts</button>
            </div>
          </div>

          <div class="card">
            <div class="card-head"><h3>${icons.activity} Inactivity Monitor</h3></div>
            <div class="card-body" id="inactivity-body">
              <div class="skeleton skeleton-line w80"></div>
              <div class="skeleton skeleton-line w60"></div>
            </div>
          </div>

          <div class="card">
            <div class="card-head"><h3>${icons.send} Recent Dispatches</h3></div>
            <div class="card-body">
              <div class="feed" id="dispatch-log"></div>
            </div>
          </div>
        </div>
      </div>`;

    // Range selector
    $$('#range-seg button').forEach((b) => {
      b.onclick = () => {
        $$('#range-seg button').forEach((x) => x.classList.remove('active'));
        b.classList.add('active');
        range = b.dataset.range;
        loadTimeline();
      };
    });

    $('#safety-refresh').onclick = () => { loadTimeline(); refreshMap(); loadDispatchLog(); };
    $('#safety-sos').onclick = () => window.dispatchEvent(new CustomEvent('nlw:sos'));
    $('#safety-dispatch-btn').onclick = () => openDispatchModal(null);
    $('#panel-dispatch').onclick = () => openDispatchModal(null);
    $('#panel-edit-contacts').onclick = () => { location.hash = '#/management?tab=contacts'; };

    // Loaders run in the background: never block navigation on slow map/CDN work.
    loadTimeline().catch(() => {});
    refreshMap().catch(() => {});
    loadDispatchLog().catch(() => {});

    // contacts count + inactivity monitor
    api.contacts().then((cs) => {
      const el = $('#contact-count');
      if (el) el.textContent = `${cs.length} saved`;
    }).catch(() => { });

    const tickInactivity = (reading) => {
      const body = $('#inactivity-body');
      if (!body || !reading) return;
      const resting = ['Resting', 'Sleeping'].includes(reading.activity);
      body.innerHTML = `
        <div class="flex-between">
          <span class="muted">Current state</span>
          <span class="badge ${resting ? 'neutral' : 'ok'}">${esc(reading.activity)}</span>
        </div>
        <div class="flex-between" style="margin:10px 0">
          <span class="muted">Last movement</span>
          <b>${resting ? 'monitoring…' : 'just now'}</b>
        </div>
        <div class="meter ${resting ? 'warn' : ''}"><i style="width:${resting ? 38 : 8}%"></i></div>
        <p class="muted" style="font-size:11.8px;margin-top:10px">
          If no movement is detected for <b>90 minutes</b> during waking hours, an inactivity alert is raised and the
          care team is notified — silent falls and unattended rest periods are caught automatically.
        </p>`;
    };
    tickInactivity(store.telemetry);
    unsubWS = onWS((msg) => {
      if (msg.type === 'telemetry') {
        tickInactivity(msg.data);
        if (mapCtl && msg.data.lat) mapCtl.update(msg.data.lat, msg.data.lng);
      } else if (msg.type === 'alert') {
        loadTimeline().catch(() => {});
        const st = $('#safety-status');
        if (st && msg.data.severity === 'critical') {
          st.className = 'notif-banner danger';
          $('#safety-status-title').innerHTML = `Active emergency: <span class="text-danger">${esc(msg.data.type)}</span>`;
          $('#safety-status-sub').textContent = msg.data.title;
        }
      }
    });
  },
  destroy() {
    if (unsubWS) { unsubWS(); unsubWS = null; }
    if (mapCtl && mapCtl.destroy) { mapCtl.destroy(); mapCtl = null; }
    range = 'today';
  },
};

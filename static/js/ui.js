/**
 * NeuroLink Wear — UI toolkit: DOM helpers, icons, toasts, modals,
 * skeleton loaders and empty states.
 */
import { localeTag } from './i18n.js?v=20261001-7';

export { localeTag };

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/* ── icons (inline SVG) ──────────────────────────────────────────────── */
export const icons = {
  heart: `<svg viewBox="0 0 24 24"><path d="M12 20.5S3.5 15 3.5 9.2C3.5 6.3 5.8 4 8.6 4c1.7 0 3.1.9 3.4 2 .3-1.1 1.7-2 3.4-2 2.8 0 5.1 2.3 5.1 5.2 0 5.8-8.5 11.3-8.5 11.3Z"/></svg>`,
  lungs: `<svg viewBox="0 0 24 24"><path d="M12 3v9"/><path d="M12 8c-1.2-1.7-3-2.2-4.7-1.5C5.2 7.4 4 9.5 4 12c0 3 .7 6 2.2 8 .7 1 2 .9 2.6-.1l2.2-3.7c.5-.8.4-1.8-.2-2.5"/><path d="M12 8c1.2-1.7 3-2.2 4.7-1.5 2.1.9 3.3 3 3.3 5.5 0 3-.7 6-2.2 8-.7 1-2 .9-2.6-.1l-2.2-3.7c-.5-.8-.4-1.8.2-2.5"/></svg>`,
  thermo: `<svg viewBox="0 0 24 24"><path d="M10 13.5V5a2 2 0 1 1 4 0v8.5a4 4 0 1 1-4 0Z"/><circle cx="12" cy="17" r="1.6"/></svg>`,
  wave: `<svg viewBox="0 0 24 24"><path d="M2 12h4l2-5 3 10 2.5-5 1.5 2h7"/></svg>`,
  activity: `<svg viewBox="0 0 24 24"><path d="M3 12h4l2.5-7 4 14 2.5-7H21"/></svg>`,
  pulse: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M8 12h2l1.5-3 2 6 1.5-3h1"/></svg>`,
  shield: `<svg viewBox="0 0 24 24"><path d="M12 2.7 4.8 5.7v5.1c0 4.6 3 8.9 7.2 10.2 4.2-1.3 7.2-5.6 7.2-10.2V5.7L12 2.7Z"/><path d="M9.2 11.9 11.3 14l3.7-3.9"/></svg>`,
  bell: `<svg viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0-6 6v3.6l-1.6 2.9a1 1 0 0 0 .9 1.5h13.4a1 1 0 0 0 .9-1.5L18 12.6V9a6 6 0 0 0-6-6Z"/><path d="M9.5 19a2.5 2.5 0 0 0 5 0"/></svg>`,
  map: `<svg viewBox="0 0 24 24"><path d="M9 3.5 3.5 6v14.5L9 18l6 2.5 5.5-2.5V3.5L15 6 9 3.5Z"/><path d="M9 3.5V18M15 6v14.5"/></svg>`,
  pin: `<svg viewBox="0 0 24 24"><path d="M12 21s6.5-5.6 6.5-10.5a6.5 6.5 0 1 0-13 0C5.5 15.4 12 21 12 21Z"/><circle cx="12" cy="10.5" r="2.3"/></svg>`,
  users: `<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.2"/><path d="M3.5 19c.6-3 2.9-4.7 5.5-4.7s4.9 1.7 5.5 4.7"/><circle cx="17.2" cy="9.2" r="2.5"/><path d="M15.6 14.7c2.4.1 4.4 1.6 4.9 4.3"/></svg>`,
  phone: `<svg viewBox="0 0 24 24"><path d="M6.5 3.5h3l1.5 4-2 1.5a11 11 0 0 0 6 6l1.5-2 4 1.5v3c0 1-.8 1.8-1.8 1.8C10.2 19.3 4.7 13.8 4.7 5.3c0-1 .8-1.8 1.8-1.8Z"/></svg>`,
  send: `<svg viewBox="0 0 24 24"><path d="m4 11.5 15.5-6.5-4.2 15.2-3.6-6.1L4 11.5Z"/><path d="m11.7 14.1 7.8-9.1"/></svg>`,
  robot: `<svg viewBox="0 0 24 24"><rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 8V5"/><circle cx="12" cy="3.8" r="1.2"/><circle cx="9" cy="13" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="13" r="1" fill="currentColor" stroke="none"/><path d="M9.5 16h5"/><path d="M4 12h-1.5M20 12h1.5"/></svg>`,
  watch: `<svg viewBox="0 0 24 24"><rect x="6.5" y="6.5" width="11" height="11" rx="3.2"/><path d="M9 6.5 9.5 3h5l.5 3.5M9 17.5 9.5 21h5l.5-3.5"/><path d="M9.5 12h1.5l1-2 1.5 4 1-2h1"/></svg>`,
  bolt: `<svg viewBox="0 0 24 24"><path d="M13 2.5 5.5 13.5H11L10 21.5l7.5-11H12l1-8Z"/></svg>`,
  check: `<svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>`,
  alert: `<svg viewBox="0 0 24 24"><path d="M12 3.5 21 19H3L12 3.5Z"/><path d="M12 10v4"/><circle cx="12" cy="16.6" r=".9" fill="currentColor" stroke="none"/></svg>`,
  info: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 11v5"/><circle cx="12" cy="7.8" r=".9" fill="currentColor" stroke="none"/></svg>`,
  inbox: `<svg viewBox="0 0 24 24"><path d="M4 13h4l1.5 3h5L16 13h4"/><path d="M5.5 5h13l2 8v5a1.5 1.5 0 0 1-1.5 1.5h-14A1.5 1.5 0 0 1 3.5 18v-5l2-8Z"/></svg>`,
  sun: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5 5l1.4 1.4M17.6 17.6 19 19M19 5l-1.4 1.4M6.4 17.6 5 19"/></svg>`,
  moon: `<svg viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/></svg>`,
  plus: `<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>`,
  trash: `<svg viewBox="0 0 24 24"><path d="M4.5 7h15"/><path d="M9 7V4.8A.8.8 0 0 1 9.8 4h4.4a.8.8 0 0 1 .8.8V7"/><path d="M6.5 7 7.4 19a1.5 1.5 0 0 0 1.5 1.4h6.2a1.5 1.5 0 0 0 1.5-1.4L17.5 7"/><path d="M10 11v6M14 11v6"/></svg>`,
  edit: `<svg viewBox="0 0 24 24"><path d="M4 20h4.5L20 8.5 15.5 4 4 15.5V20Z"/><path d="m13.5 6 4.5 4.5"/></svg>`,
  refresh: `<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.7-6"/><path d="M20 4v5h-5"/></svg>`,
  settings: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L14.2 3h-4l-.4 2.7a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5a7 7 0 0 0 0 2.4l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2l.4 2.7h4l.4-2.7a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5c.06-.4.1-.8.1-1.2Z"/></svg>`,
  wifi: `<svg viewBox="0 0 24 24"><path d="M3.5 9a13 13 0 0 1 17 0"/><path d="M6.8 12.3a8.4 8.4 0 0 1 10.4 0"/><path d="M10 15.6a3.8 3.8 0 0 1 4 0"/><circle cx="12" cy="18.8" r="1" fill="currentColor" stroke="none"/></svg>`,
  clock: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>`,
  walk: `<svg viewBox="0 0 24 24"><circle cx="13" cy="4.5" r="1.8"/><path d="M11 21l1.8-5.2-2.3-2.2.8-4.6 3.2 1.7 2.5.6"/><path d="m9.3 9.6-2.6 1.2-1.2 2.4"/><path d="m12.5 15.8 2.7 1.9.9 3.3"/></svg>`,
  calendar: `<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M8 2.8V7M16 2.8V7M3.5 10h17"/></svg>`,
};

/* ── formatters ──────────────────────────────────────────────────────── */
export const fmtTime = (ts) => {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleTimeString(localeTag(), { hour: '2-digit', minute: '2-digit' });
};
export const fmtDateTime = (ts) => {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleString(localeTag(), {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
};
export const fmtRelative = (ts) => {
  if (!ts) return '—';
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 10) return 'just now';
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};
export const fmtDate = (ts) => {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString(localeTag(), { weekday: 'short', month: 'short', day: 'numeric' });
};
export const fmtNum = (n, digits = 0) =>
  (n === null || n === undefined || Number.isNaN(n)) ? '—'
    : Number(n).toLocaleString(localeTag(), { maximumFractionDigits: digits, minimumFractionDigits: digits });

export const severityOf = (sev) => ({
  critical: 'critical', high: 'high', medium: 'medium', low: 'low',
}[sev] || 'low');

export const typeIcon = (type) => {
  const t = (type || '').toLowerCase();
  if (t.includes('fall')) return icons.activity;
  if (t.includes('oxygen') || t.includes('spo')) return icons.lungs;
  if (t.includes('fever') || t.includes('temp')) return icons.thermo;
  if (t.includes('stress') || t.includes('panic')) return icons.wave;
  if (t.includes('heart') || t.includes('cardia')) return icons.heart;
  if (t.includes('inactivity')) return icons.clock;
  if (t.includes('sos') || t.includes('emergency')) return icons.shield;
  return icons.pulse;
};

/* ── skeleton helpers ────────────────────────────────────────────────── */
export const skeletonCards = (n = 4, cls = 'skeleton-card') =>
  `<div class="grid cols-${Math.min(n, 4)}">${Array.from({ length: n }, () =>
    `<div class="skeleton ${cls}"></div>`).join('')}</div>`;

export const skeletonLines = (n = 3) =>
  Array.from({ length: n }, (_, i) =>
    `<div class="skeleton skeleton-line ${['w80', 'w60', 'w40'][i % 3]}"></div>`).join('');

export const skeletonChart = () => `<div class="skeleton skeleton-chart"></div>`;

/* ── empty states ────────────────────────────────────────────────────── */
export function emptyState({ icon = icons.inbox, title = 'Nothing here yet', body = '', action = '' }) {
  return `
    <div class="empty-state">
      <div class="empty-icon">${icon}</div>
      <h4>${esc(title)}</h4>
      <p>${body}</p>
      ${action}
    </div>`;
}

/* ── toasts ──────────────────────────────────────────────────────────── */
export function toast(type, title, body = '', timeout = 5200) {
  const root = $('#toast-root');
  const el = document.createElement('div');
  const iconMap = {
    success: icons.check, error: icons.alert, warning: icons.alert,
    info: icons.info, alert: icons.bell,
  };
  el.className = `toast ${type}`;
  el.innerHTML = `
    <div class="t-icon">${iconMap[type] || icons.info}</div>
    <div><strong>${esc(title)}</strong>${body ? `<p>${esc(body)}</p>` : ''}</div>`;
  root.appendChild(el);
  const kill = () => {
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 260);
  };
  el.addEventListener('click', kill);
  if (timeout) setTimeout(kill, timeout);
  return el;
}

/* ── modal ───────────────────────────────────────────────────────────── */
let modalCloseCb = null;
export function openModal({ title, body, footer = '', wide = false, onClose = null }) {
  const root = $('#modal-root');
  modalCloseCb = onClose;
  root.classList.remove('hidden');
  root.innerHTML = `
    <div class="modal ${wide ? 'wide' : ''}" role="dialog" aria-modal="true">
      <div class="modal-head">
        <h3>${title}</h3>
        <button class="icon-btn" data-modal-close aria-label="Close">✕</button>
      </div>
      <div class="modal-body">${body}</div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : '<div style="height:14px"></div>'}
    </div>`;
  root.onclick = (e) => {
    if (e.target === root || e.target.closest('[data-modal-close]')) closeModal();
  };
  const escHandler = (e) => { if (e.key === 'Escape') closeModal(); };
  document.addEventListener('keydown', escHandler, { once: true });
  return root.querySelector('.modal');
}
export function closeModal() {
  const root = $('#modal-root');
  root.classList.add('hidden');
  root.innerHTML = '';
  if (modalCloseCb) { modalCloseCb(); modalCloseCb = null; }
}

/** Confirm dialog returning a promise. */
export function confirmDialog(title, body, confirmLabel = 'Delete') {
  return new Promise((resolve) => {
    let decided = false;
    openModal({
      title,
      body: `<p class="muted" style="font-size:calc(13.5px * var(--fs))">${body}</p>`,
      footer: `
        <button class="btn ghost" data-modal-close>Cancel</button>
        <button class="btn danger" id="confirm-yes">${confirmLabel}</button>`,
      onClose: () => { if (!decided) resolve(false); },
    });
    $('#confirm-yes').onclick = () => {
      decided = true;
      closeModal();
      resolve(true);
    };
  });
}

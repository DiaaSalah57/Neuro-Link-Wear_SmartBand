/**
 * NeuroLink Wear — accessibility preferences shared by every screen:
 *   • Language toggle  (English ⇄ العربية)  → delegates to i18n.js
 *   • Text size        (Normal / Large / Extra large) for elderly readers
 *
 * Both controls live in the status banner and on the sign-in screen, so the
 * elderly user can make the dashboard readable *before* logging in. Settings
 * (System → Settings) exposes the same options as an explicit segmented list.
 *
 * Wiring is delegated from the document, so buttons rendered later (Settings
 * view, re-rendered shell) keep working without re-binding.
 */
import { getLang, setLang, initI18n, LANG_META } from './i18n.js?v=20261001-8';

export const FONT_LEVELS = [
  {
    id: 'normal', scale: 1, pct: 100,
    label: 'Normal',
    hint: 'Text size: Normal (100%). Click to increase.',
  },
  {
    id: 'large', scale: 1.18, pct: 118,
    label: 'Large',
    hint: 'Text size: Large (118%). Click to increase.',
  },
  {
    id: 'xlarge', scale: 1.38, pct: 138,
    label: 'Extra large',
    hint: 'Text size: Extra large (138%). Click to reset to Normal.',
  },
];

const FONT_KEY = 'nlw_fontsize';

const levelIndex = (id) => Math.max(0, FONT_LEVELS.findIndex((l) => l.id === id));
export const getFontLevel = () => FONT_LEVELS[levelIndex(document.documentElement.dataset.fontsize || 'normal')];

function readSavedFont() {
  try {
    const saved = localStorage.getItem(FONT_KEY);
    if (FONT_LEVELS.some((l) => l.id === saved)) return saved;
  } catch { /* storage blocked */ }
  return 'normal';
}

/** Apply a text-size level to the document + keep every control in sync. */
export function setFontLevel(id, { persist = true } = {}) {
  const level = FONT_LEVELS[levelIndex(id)];
  const html = document.documentElement;
  html.dataset.fontsize = level.id;
  html.style.setProperty('--fs', String(level.scale));
  if (persist) {
    try { localStorage.setItem(FONT_KEY, level.id); } catch { /* memory-only */ }
  }
  syncControls();
  return level;
}

export function cycleFontLevel() {
  const cur = levelIndex(document.documentElement.dataset.fontsize || 'normal');
  return setFontLevel(FONT_LEVELS[(cur + 1) % FONT_LEVELS.length].id);
}

/** Refresh labels / active states of every language & text-size control. */
export function syncControls() {
  const lang = getLang();
  const level = getFontLevel();
  const other = lang === 'ar' ? 'en' : 'ar';

  document.querySelectorAll('[data-pref="lang"]').forEach((el) => {
    const label = el.querySelector('[data-pref-label]') || el;
    label.textContent = LANG_META[other].label;
    const hint = other === 'ar'
      ? 'Switch to Arabic — التبديل إلى العربية'
      : 'Switch to English — التبديل إلى الإنجليزية';
    el.setAttribute('title', hint);
    el.setAttribute('aria-label', hint);
    el.dataset.lang = other;
    el.setAttribute('aria-pressed', String(lang === 'ar'));
  });

  document.querySelectorAll('[data-pref="font"]').forEach((el) => {
    el.dataset.level = level.id;
    el.setAttribute('title', level.hint);
    el.setAttribute('aria-label', level.hint);
    const pct = el.querySelector('[data-pref-pct]');
    if (pct) pct.textContent = `${level.pct}%`;
  });

  document.querySelectorAll('[data-font-size]').forEach((btn) => {
    const on = btn.dataset.fontSize === level.id;
    btn.classList.toggle('active', on);
    btn.setAttribute('aria-pressed', String(on));
  });

  document.querySelectorAll('button[data-lang]:not([data-pref="lang"])').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
    btn.setAttribute('aria-pressed', String(btn.dataset.lang === lang));
  });
}

/* ── delegated wiring ─────────────────────────────────────────────────── */
function onClick(e) {
  const langBtn = e.target.closest('[data-pref="lang"], button[data-lang]');
  if (langBtn && !langBtn.disabled) {
    const next = langBtn.dataset.lang || (getLang() === 'ar' ? 'en' : 'ar');
    if (next !== getLang()) setLang(next);
    else syncControls();
    return;
  }
  const fontBtn = e.target.closest('[data-pref="font"], [data-font-size]');
  if (fontBtn && !fontBtn.disabled) {
    if (fontBtn.dataset.pref === 'font') cycleFontLevel();
    else setFontLevel(fontBtn.dataset.fontSize);
  }
}

/**
 * Boot accessibility preferences. Safe to call once, early (before the first
 * view renders) so the saved language and text size are in place immediately.
 */
export function initPrefs() {
  setFontLevel(readSavedFont(), { persist: false });
  initI18n();
  document.addEventListener('click', onClick);
  window.addEventListener('nlw:lang', syncControls);
  // Views render their own copies of the controls (Settings, login) — refresh
  // labels only when such a control actually enters the DOM.
  new MutationObserver((records) => {
    const hasControls = records.some((r) => [...r.addedNodes].some((n) => n.nodeType === 1
      && (n.matches?.('[data-pref],[data-font-size],button[data-lang]')
        || n.querySelector?.('[data-pref],[data-font-size],button[data-lang]'))));
    if (hasControls) syncControls();
  }).observe(document.body, { childList: true, subtree: true });
  syncControls();
}

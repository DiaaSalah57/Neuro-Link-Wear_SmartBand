/**
 * NeuroLink Wear — runtime i18n engine (English ⇄ Arabic).
 *
 * The dashboard has no build step: every view renders English template
 * strings straight into the DOM. Instead of rewriting every view, this module
 * translates the *rendered DOM* — text nodes plus labels/placeholders/titles —
 * and keeps translating anything the app injects later through a
 * MutationObserver. That way toasts, modals, live telemetry values and
 * dynamically re-rendered cards are covered automatically.
 *
 * Matching strategy (per text node / attribute):
 *   1. normalise whitespace, look up an exact English → Arabic entry;
 *   2. otherwise try the ordered dynamic *rules* (numbers, names, units).
 * The original English string is remembered on the node so switching back to
 * English restores it byte-for-byte and the pass is idempotent.
 *
 * Language state is persisted in localStorage (`nlw_lang`) and reflected on
 * <html lang dir>, so CSS can flip the layout to RTL. A `nlw:lang` event is
 * dispatched after every change (the shell re-renders the active view so
 * locale-aware date/number formatting picks up the new locale).
 */
import { exact as AR_EXACT_TABLE, rules as AR_RULES } from './locales/ar.js?v=20261001-7';

export const LANGS = ['en', 'ar'];
export const LANG_META = {
  en: { label: 'English', short: 'EN', dir: 'ltr' },
  ar: { label: 'العربية', short: 'ع', dir: 'rtl' },
};

const STORAGE_KEY = 'nlw_lang';
const TITLE_EN = 'NeuroLink Wear — Health & Safety Dashboard';
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'CODE', 'PRE']);
const TRANSLATED_ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];
/* Latin-only text is candidate for translation; skip rules for long bodies
   such as server-generated narratives (left in English on purpose). */
// Rules are tried in order on every untranslated string. Anchored patterns fail
// fast on a mismatch, so the ceiling is set by the longest AI-narrative template
// (~311 chars) rather than by a performance concern.
const RULE_MAX_LEN = 420;

const AR_EXACT = new Map(Object.entries(AR_EXACT_TABLE));

/** HTML <title> lives in <head>; SVG <title> is a chart tooltip (translatable). */
const isHtmlTitle = (el) => el.tagName === 'TITLE' && el.namespaceURI !== 'http://www.w3.org/2000/svg';

let current = 'en';
let observer = null;
let applyQueued = false;
const listeners = new Set();

/* ── language state ───────────────────────────────────────────────────── */
export function getLang() {
  return current;
}

/** BCP-47 tag used for date/number formatting (Latin digits in Arabic). */
export function localeTag() {
  return current === 'ar' ? 'ar-EG-u-nu-latn' : undefined;
}

export function isRTL() {
  return current === 'ar';
}

function readSavedLang() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && LANGS.includes(saved)) return saved;
  } catch { /* storage blocked */ }
  // First visit: honour the browser language, defaulting to English.
  const nav = (navigator.language || 'en').toLowerCase();
  return nav.startsWith('ar') ? 'ar' : 'en';
}

export function onLangChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function setLang(next, { persist = true } = {}) {
  const lang = LANGS.includes(next) ? next : 'en';
  if (persist) {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* memory-only */ }
  }
  const changed = lang !== current;
  current = lang;
  applyLang();
  if (changed) {
    listeners.forEach((fn) => { try { fn(lang); } catch (e) { console.error('[i18n]', e); } });
    window.dispatchEvent(new CustomEvent('nlw:lang', { detail: { lang } }));
  }
  return lang;
}

/** Apply the current language to the document (dir/lang/title + DOM pass). */
export function applyLang() {
  const html = document.documentElement;
  html.lang = current;
  html.dir = current === 'ar' ? 'rtl' : 'ltr';
  html.dataset.lang = current;

  if (document.body) {
    document.title = current === 'ar' ? (lookup(TITLE_EN) || TITLE_EN) : TITLE_EN;
    translateTree(document.body);
  }
}

/* ── translation core ─────────────────────────────────────────────────── */

/** Collapse whitespace so multi-line template strings match single-spaced keys. */
const norm = (s) => s.replace(/\s+/g, ' ').trim();

/**
 * Translate one English string (with any surrounding whitespace preserved).
 * Returns null when there is nothing to translate.
 */
export function lookup(raw) {
  if (!raw || !/[A-Za-z]/.test(raw)) return null;
  const lead = raw.match(/^\s*/)[0];
  const tail = raw.match(/\s*$/)[0];
  const core = norm(raw);
  if (!core) return null;

  let out = AR_EXACT.get(core);
  if (!out && core.length <= RULE_MAX_LEN) {
    for (const rule of AR_RULES) {
      const m = rule.re.exec(core);
      if (m) {
        out = typeof rule.to === 'function' ? rule.to(m) : core.replace(rule.re, rule.to);
        break;
      }
    }
  }
  if (!out) return null;
  return lead + out + tail;
}

/** Public helper — translate a bare string (no node bookkeeping). */
export function t(str) {
  if (current !== 'ar') return str;
  return lookup(str) || str;
}

function translateTextNode(node) {
  const parent = node.parentElement;
  if (parent && (SKIP_TAGS.has(parent.tagName) || parent.closest('[data-no-i18n]'))) return;
  if (parent && (isHtmlTitle(parent) || parent.tagName === 'desc')) return;

  const cur = node.nodeValue;
  if (!cur) return;
  // A node that was translated before must be revisited even when it now holds
  // pure Arabic text (that is exactly the state we need to restore from).
  const known = node.__nlwSrc !== undefined;
  if (!known && !/[A-Za-z]/.test(cur)) return;

  if (!known || (node.__nlwTr !== undefined && cur !== node.__nlwTr)) {
    // The app rewrote the node since our last pass → adopt the new English text.
    if (!/[A-Za-z]/.test(cur)) { delete node.__nlwSrc; delete node.__nlwTr; return; }
    node.__nlwSrc = cur;
  }
  const src = node.__nlwSrc;

  if (current === 'ar') {
    const out = lookup(src);
    if (!out) { node.__nlwTr = cur; return; }
    if (cur !== out) node.nodeValue = out;
    node.__nlwTr = out;
  } else {
    if (cur !== src) node.nodeValue = src;
    node.__nlwTr = src;
  }
}

function translateAttr(el, attr) {
  if (el.closest('[data-no-i18n]')) return;
  const cur = el.getAttribute(attr);
  if (cur === null || cur === '') return;
  el.__nlwA = el.__nlwA || {};
  const memo = el.__nlwA[attr];
  const known = memo && memo.src !== undefined;
  if (!known && !/[A-Za-z]/.test(cur)) return;

  if (!known || (memo.tr !== undefined && cur !== memo.tr)) {
    if (!/[A-Za-z]/.test(cur)) { delete el.__nlwA[attr]; return; }
    el.__nlwA[attr] = { src: cur };
  }
  const { src } = el.__nlwA[attr];

  if (current === 'ar') {
    const out = lookup(src);
    if (!out) { el.__nlwA[attr].tr = cur; return; }
    if (cur !== out) el.setAttribute(attr, out);
    el.__nlwA[attr].tr = out;
  } else {
    if (cur !== src) el.setAttribute(attr, src);
    el.__nlwA[attr].tr = src;
  }
}

function translateAttrs(el) {
  for (const attr of TRANSLATED_ATTRS) {
    if (el.hasAttribute(attr)) translateAttr(el, attr);
  }
}

function isSkippedElement(el) {
  return SKIP_TAGS.has(el.tagName)
    || isHtmlTitle(el)          // SVG <title> (chart tooltips) is translated
    || el.tagName === 'desc'
    || !!el.closest('[data-no-i18n]');
}

function translateElement(el) {
  if (!(el instanceof Element)) return;
  if (isSkippedElement(el)) return;
  translateAttrs(el);
  // Walk elements *and* text nodes: element nodes carry translated attributes
  // (title / aria-label / placeholder) further down the subtree.
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      if (n.nodeType === Node.ELEMENT_NODE) {
        return isSkippedElement(n) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
      const p = n.parentElement;
      if (!p) return NodeFilter.FILTER_REJECT;
      if (SKIP_TAGS.has(p.tagName) || isHtmlTitle(p) || p.tagName === 'desc') {
        return NodeFilter.FILTER_REJECT;
      }
      return p.closest('[data-no-i18n]') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
    },
  });
  let n = walker.nextNode();
  while (n) {
    if (n.nodeType === Node.ELEMENT_NODE) translateAttrs(n);
    else translateTextNode(n);
    n = walker.nextNode();
  }
}

/** Translate a subtree (or the whole document when no root is given). */
export function translateTree(root = document.body) {
  if (!root) return;
  if (root.nodeType === Node.TEXT_NODE) { translateTextNode(root); return; }
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  translateElement(root);
}

/* ── live observation: keep dynamically rendered content translated ────── */
function scheduleApply(records) {
  for (const record of records) {
    if (record.type === 'characterData') {
      translateTextNode(record.target);
    } else if (record.type === 'childList') {
      record.addedNodes.forEach((n) => translateTree(n));
    } else if (record.type === 'attributes') {
      translateAttr(record.target, record.attributeName);
    }
  }
}

export function observeI18n() {
  if (observer || !document.body) return;
  let pending = [];
  observer = new MutationObserver((records) => {
    pending = pending.concat(records);
    if (applyQueued) return;
    applyQueued = true;
    queueMicrotask(() => {
      applyQueued = false;
      const batch = pending;
      pending = [];
      try {
        scheduleApply(batch);
      } catch (err) {
        console.error('[i18n]', err);
      }
    });
  });
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: TRANSLATED_ATTRS,
  });
}

/** Boot: restore the saved language and start observing the DOM. */
export function initI18n() {
  current = readSavedLang();
  applyLang();
  observeI18n();
  return current;
}

export function toggleLang() {
  return setLang(current === 'ar' ? 'en' : 'ar');
}

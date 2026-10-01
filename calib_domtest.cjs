#!/usr/bin/env node
/**
 * NeuroLink Wear — jsdom DOM smoke suite (`calib_domtest.cjs`, 17 checks).
 *
 * Verifies:
 *  1-4. Sign-in regression (wrong password -> "Invalid email or password", never "session expired")
 *  5-6. Valid caregiver login -> dashboard shell renders
 *  7-13. Management -> Calibration tab renders (title, auto-fit button, 8 baseline inputs
 *        with source badges, two-tier panels, live equation panel)
 *  14. Auto-fit button interaction re-renders cleanly
 *  15-16. Guided oral reference applies and appears in Reference history
 *  17. Personal σ-rule slider updates & saves
 */
const { JSDOM, VirtualConsole } = require('jsdom');

const BASE = 'http://127.0.0.1:8000';
let pass = 0;
const failed = [];

function check(name, cond, detail = '') {
  if (cond) {
    pass += 1;
    console.log(`  ✓ ${name}`);
  } else {
    failed.push(name);
    console.log(`  ✗ FAIL: ${name} ${detail}`);
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  console.log('\n── calib_domtest.cjs (17 DOM checks) ──');
  const htmlRes = await fetch(`${BASE}/`);
  const html = await htmlRes.text();

  const vc = new VirtualConsole();
  const pageErrors = [];
  vc.on('jsdomError', (e) => {
    if (!String(e.message || '').includes('Not implemented')) pageErrors.push(e.message);
  });

  const dom = new JSDOM(html, {
    url: `${BASE}/`,
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    virtualConsole: vc,
  });

  const { window } = dom;
  const { document } = window;
  const rawNodeFetch = globalThis.fetch.bind(globalThis);

  // Polyfill fetch + WebSocket for both window and globalThis
  const patchedFetch = (url, opts = {}) => {
    const full = String(url).startsWith('http') ? url : `${BASE}${url}`;
    return rawNodeFetch(full, opts);
  };
  window.fetch = patchedFetch;
  globalThis.fetch = patchedFetch;
  window.WebSocket = class DummyWS {
    constructor() { setTimeout(() => this.onopen && this.onopen(), 10); }
    send() {}
    close() {}
  };
  globalThis.WebSocket = window.WebSocket;

  // Load ES module entry point via dynamic import workaround or script evaluation
  // Wait for scripts/DOM ready, or boot app modules directly
  await sleep(600);

  // If JSDOM didn't execute <script type="module">, import and mount views directly against JSDOM globals
  globalThis.window = window;
  globalThis.document = document;
  globalThis.localStorage = window.localStorage;
  globalThis.sessionStorage = window.sessionStorage;
  globalThis.location = window.location;
  globalThis.CustomEvent = window.CustomEvent;
  globalThis.HTMLElement = window.HTMLElement;

  const loginMod = await import('./static/js/views/login.js?v=20261001-4');
  const mgmtMod = await import('./static/js/views/management.js?v=20261001-4');
  const alertsMod = await import('./static/js/views/alerts.js?v=20261001-4');
  const { api, auth } = await import('./static/js/api.js?v=20261001-4');

  loginMod.default.render();

  // 1. Login screen visible
  check('1. Login screen visible on cold boot', !document.querySelector('#login-screen').classList.contains('hidden'));

  // 2-4. Wrong password sign-in regression
  document.querySelector('#login-email').value = 'caregiver@neurolink.health';
  document.querySelector('#login-password').value = 'wrong-password-123';
  await document.querySelector('#login-form').onsubmit({ preventDefault() {} });
  const errText = document.querySelector('#login-error').textContent.trim();
  check('2. Wrong password shows error box', !document.querySelector('#login-error').classList.contains('hidden'));
  check('3. Wrong password message is "Invalid email or password"', errText.includes('Invalid email or password'), `got="${errText}"`);
  check('4. Wrong password never says "Session expired"', !errText.toLowerCase().includes('session expired'), `got="${errText}"`);

  // 5-6. Demo chip + valid sign-in
  const caregiverChip = document.querySelector('.demo-chip[data-email="caregiver@neurolink.health"]');
  caregiverChip.click();
  check('5. Caregiver demo chip autofills email', document.querySelector('#login-email').value === 'caregiver@neurolink.health');
  await document.querySelector('#login-form').onsubmit({ preventDefault() {} });
  check('6. Valid login stores session token & user', Boolean(auth.token && auth.user && auth.user.name));

  // 7-13. Render Management -> Calibration tab
  const viewRoot = document.querySelector('#view-root');
  await mgmtMod.default.render(viewRoot, { params: { tab: 'calibration' } });
  await sleep(150);

  const calText = viewRoot.textContent;
  check('7. Calibration tab title renders', calText.includes('Calibration — personalised'));
  check('8. Auto-fit button present', Boolean(viewRoot.querySelector('#cal-autofit')));
  const baseInputs = viewRoot.querySelectorAll('[data-cal-base]');
  check('9. All 8 personal baseline inputs rendered', baseInputs.length === 8, `count=${baseInputs.length}`);
  check('10. Baseline source badges rendered', viewRoot.querySelectorAll('.field .badge').length >= 8);
  check('11. Tier 1 clinical floors panel rendered', calText.includes('Tier 1 · clinical floors') && calText.includes('Never personalised'));
  check('12. Tier 2 personal σ-rules panel rendered', calText.includes('Tier 2 · personal σ-rules') && Boolean(viewRoot.querySelector('#cal-z-slider')));
  check('13. Guided reference measurements panel rendered', calText.includes('Guided reference measurements') && Boolean(viewRoot.querySelector('#cal-ref-add')));

  // 14. Auto-fit interaction
  await viewRoot.querySelector('#cal-autofit').onclick();
  await sleep(150);
  check('14. Auto-fit re-renders Calibration tab cleanly', Boolean(viewRoot.querySelector('#cal-autofit')));

  // 15-16. Guided oral reference measurement applies & appears in Reference history
  viewRoot.querySelector('#cal-ref-kind').value = 'oral_temp';
  viewRoot.querySelector('#cal-ref-value').value = '37.1';
  viewRoot.querySelector('#cal-ref-band').value = '36.3';
  viewRoot.querySelector('#cal-ref-note').value = 'domtest oral ref';
  await viewRoot.querySelector('#cal-ref-add').onclick();
  await sleep(150);
  const newOffset = Number(viewRoot.querySelector('[data-cal-base="temp_offset"]').value);
  check('15. Guided oral reference updates temp_offset', Math.abs(newOffset - 0.8) < 0.05, `offset=${newOffset}`);
  check('16. Reference history table lists oral temp entry', viewRoot.textContent.includes('Reference history') && viewRoot.textContent.includes('oral temp'));

  // 17. Personal σ-rule slider updates and saves
  const zSlider = viewRoot.querySelector('#cal-z-slider');
  zSlider.value = '2.2';
  zSlider.oninput();
  await viewRoot.querySelector('#cal-rules-save').onclick();
  await sleep(150);
  check('17. Personal σ-rule slider saves and persists', Number(viewRoot.querySelector('#cal-z-slider').value) === 2.2);

  // Bonus verification: Tier 3 General Anomaly alert badge & ML score in Alerts view
  await globalThis.fetch(`${BASE}/api/telemetry/ingest?device_key=neurolink-demo-key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      Heart_Rate: 108, Body_Temperature: 36.6, Blood_Oxygen: 93.0,
      GSR_Value: 0.5, HRV: 45,
      Accel_X: -2.5, Accel_Y: 0.8, Accel_Z: -0.5,
      Gyro_X: 1.6, Gyro_Y: -1.4, Gyro_Z: 0.8,
      Activity_Status: 'Running', Step_Count: 8500, Sweat_Response: 15.5,
    }),
  });
  await alertsMod.default.render(viewRoot, { params: {} });
  await sleep(150);
  const mlCard = viewRoot.querySelector('[data-alert-type="General Anomaly"]');
  const mlBadge = mlCard && mlCard.querySelector('.ml-tier-badge');
  const mlDetail = mlCard && mlCard.querySelector('[data-ml-detail="1"]');
  if (!mlCard || !mlBadge || !mlDetail || !mlDetail.textContent.includes('Isolation Forest score')) {
    console.log('  ✗ FAIL: Tier 3 General Anomaly badge/score in Alerts view');
    failed.push('Tier 3 General Anomaly DOM check');
  } else {
    console.log('  ✓ Bonus: Tier 3 "General Anomaly" renders ML Model badge + Isolation Forest score in Alerts view');
  }

  console.log(`\n============================================================`);
  console.log(`  DOM TOTAL: ${pass}/17 passed, ${failed.length} failed`);
  if (failed.length) process.exit(1);
  console.log('  🧪 CALIB DOM SUITE: PASS');
})();

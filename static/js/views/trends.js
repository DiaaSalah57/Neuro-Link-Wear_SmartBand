/**
 * NeuroLink Wear — Historical Trends & Analytics:
 * interactive time-series charts (HRV, temperature, stress, HR) with
 * date-range filters and daily activity summaries.
 */
import { api } from '../api.js?v=20261001-3';
import {
  $, $$, esc, icons, fmtNum, fmtDate, skeletonChart, skeletonCards,
  emptyState,
} from '../ui.js?v=20261001-3';
import { lineChart, barChart, donutChart } from '../charts.js?v=20261001-3';

let rangeHours = 24;

const PALETTE = {
  hrv: '#170c5e', temp: '#8f82ee', stress: '#a79bf2', hr: '#241483',
  spo2: '#5b4bd6', steps: '#3d2db8', active: '#6b5ae8',
};

function statTile({ label, value, unit = '', delta = null, deltaLabel = 'vs prev. 24h', tone = 'neutral' }) {
  return `
  <div class="card stat-tile">
    <div class="label">${label}</div>
    <div class="value">${value}<span style="font-size:13px;color:var(--muted);margin-left:3px">${unit}</span></div>
    ${delta !== null ? `<div class="delta ${tone}">${delta > 0 ? '▲' : delta < 0 ? '▼' : '→'} ${fmtNum(Math.abs(delta), Math.abs(delta) < 1 ? 2 : 1)} <span class="muted" style="font-weight:500">${deltaLabel}</span></div>` : '<div class="delta neutral">—</div>'}
  </div>`;
}

async function renderCharts() {
  if (!document.getElementById('chart-hrv')) return;
  const histBox = $('#chart-vitals');
  const hrvBox = $('#chart-hrv');
  const stressBox = $('#chart-stress');
  [histBox, hrvBox, stressBox].forEach((b) => { if (b) b.innerHTML = skeletonChart(); });

  const [hist, thresholds] = await Promise.all([
    api.history(rangeHours, 480),
    api.thresholds().catch(() => null),
  ]);
  const data = hist.data;
  if (!data.length) {
    const msg = emptyState({
      icon: icons.activity, title: 'No readings in this range',
      body: 'Try a wider date range — the band stores 30 days of history.',
    });
    if (histBox) histBox.innerHTML = msg;
    if (hrvBox) hrvBox.innerHTML = msg;
    if (stressBox) stressBox.innerHTML = msg;
    return;
  }

  const pts = (key) => data.map((d) => ({ t: d.ts, v: d[key] }));
  const timeFmt = rangeHours <= 48
    ? (d) => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : (d) => d.toLocaleDateString([], { month: 'short', day: 'numeric' });

  // HRV + temperature combined (dual series, normalized scale each own axis is
  // complex — render two stacked panels instead)
  lineChart(hrvBox, [
    { name: 'HRV (ms)', color: PALETTE.hrv, points: pts('hrv') },
  ], { height: 220, unit: ' ms', yDigits: 0, timeFormat: timeFmt, refLines: thresholds ? [{ v: thresholds.hrv_low, label: `fatigue < ${thresholds.hrv_low}`, color: '#f59e0b' }] : [] });

  lineChart(histBox, [
    { name: 'Skin temperature (°C)', color: PALETTE.temp, points: pts('temperature') },
    { name: 'SpO₂ (%)', color: PALETTE.spo2, points: pts('spo2'), dashed: true },
  ], {
    height: 250, yDigits: 1, timeFormat: timeFmt, showLegend: true,
    refLines: thresholds
      ? [{ v: thresholds.temp_high, label: `fever > ${thresholds.temp_high}°C`, color: '#241483' }]
      : [],
  });

  lineChart(stressBox, [
    { name: 'Stress index', color: PALETTE.stress, points: pts('stress_score') },
    { name: 'Heart rate (bpm ÷ 120)', color: PALETTE.hr, points: data.map((d) => ({ t: d.ts, v: d.heart_rate / 120 })) },
  ], {
    height: 230, yDigits: 2, timeFormat: timeFmt,
    refLines: thresholds ? [{ v: thresholds.stress_high, label: `high stress > ${thresholds.stress_high}`, color: '#a79bf2' }] : [],
  });
}

async function renderActivity() {
  if (!document.getElementById('chart-activity')) return;
  const box = $('#chart-activity');
  const donut = $('#chart-activity-donut');
  if (box) box.innerHTML = skeletonChart();
  const res = await api.activity(14).catch(() => ({ days: [], today_activity: [] }));

  if (!res.days.length) {
    if (box) box.innerHTML = emptyState({ icon: icons.walk, title: 'No activity history', body: 'Daily summaries appear after the band has streamed for a day.' });
    return;
  }
  const labels = res.days.map((d) => fmtDate(`${d.date}T12:00:00`).split(',').pop().trim());
  barChart(box, labels, [
    { name: 'Steps', color: PALETTE.steps, values: res.days.map((d) => d.steps) },
    { name: 'Active minutes', color: PALETTE.active, values: res.days.map((d) => d.active_minutes * 20) },
  ], { height: 230 });

  if (donut) {
    const act = res.today_activity || [];
    const colors = { Sleeping: '#170c5e', Resting: '#b0a9d0', Walking: '#5b4bd6', Running: '#241483', Exercising: '#8f82ee' };
    const total = act.reduce((a, x) => a + x.n, 0);
    if (total) {
      donutChart(donut, act.map((x) => ({ name: x.activity, value: x.n, color: colors[x.activity] || '#241483' })),
        { centerLabel: `${total} pts` });
    } else {
      donut.innerHTML = `<div class="muted" style="font-size:12.5px">Activity breakdown appears once live readings accumulate.</div>`;
    }
  }
}

export default {
  async render(root) {
    root.innerHTML = `
      <div class="page-head">
        <div>
          <h2>Historical Trends &amp; Analytics</h2>
          <div class="subtitle">Interactive time-series for HRV, body temperature, stress variation and daily activity — with clinical thresholds overlaid.</div>
        </div>
        <div class="page-actions">
          <div class="segmented" id="trend-range">
            <button data-hours="24" class="active">24 h</button>
            <button data-hours="48">48 h</button>
            <button data-hours="168">7 days</button>
            <button data-hours="720">30 days</button>
          </div>
        </div>
      </div>

      <div class="grid cols-4" id="kpi-grid">
        ${skeletonCards(4, 'skeleton-card')}
      </div>

      <div class="grid cols-2" style="margin-top:16px">
        <div class="card">
          <div class="card-head"><h3>${icons.heart} Heart-Rate Variability</h3><span class="sub">autonomic recovery marker</span></div>
          <div class="card-body" id="chart-hrv"></div>
        </div>
        <div class="card">
          <div class="card-head"><h3>${icons.thermo} Temperature &amp; SpO₂</h3><span class="sub">fever / desaturation watch</span></div>
          <div class="card-body" id="chart-vitals"></div>
        </div>
      </div>

      <div class="card" style="margin-top:16px">
        <div class="card-head"><h3>${icons.wave} Stress Index vs Heart Rate</h3><span class="sub">GSR + HRV composite stress score</span></div>
        <div class="card-body" id="chart-stress"></div>
      </div>

      <div class="grid span-right" style="margin-top:16px">
        <div class="card">
          <div class="card-head"><h3>${icons.walk} Daily Activity Summary — 14 days</h3><span class="sub">steps &amp; active minutes</span></div>
          <div class="card-body" id="chart-activity"></div>
        </div>
        <div class="card">
          <div class="card-head"><h3>${icons.activity} Today's motion mix</h3></div>
          <div class="card-body" id="chart-activity-donut"></div>
          <div class="card-body" style="padding-top:0" id="activity-facts">
            <div class="skeleton skeleton-line w80"></div>
            <div class="skeleton skeleton-line w60"></div>
          </div>
        </div>
      </div>`;

    $$('#trend-range button').forEach((b) => {
      b.onclick = () => {
        $$('#trend-range button').forEach((x) => x.classList.remove('active'));
        b.classList.add('active');
        rangeHours = +b.dataset.hours;
        renderCharts();
      };
    });

    const load = async () => {
      const [stats] = await Promise.all([
        api.stats().catch(() => null),
        renderCharts(),
        renderActivity(),
      ]);
      const grid = $('#kpi-grid');
      if (grid && stats && stats.window_24h && stats.window_24h.n > 0) {
        const w = stats.window_24h;
        const d = stats.delta_vs_prev || {};
        grid.innerHTML = [
          statTile({
            label: 'Avg heart rate (24h)', value: fmtNum(w.hr, 0), unit: 'bpm',
            delta: d.hr ?? null, tone: (d.hr ?? 0) > 4 ? 'up' : (d.hr ?? 0) < -4 ? 'down' : 'neutral',
          }),
          statTile({
            label: 'Avg HRV (24h)', value: fmtNum(w.hrv, 0), unit: 'ms',
            delta: d.hrv ?? null, tone: (d.hrv ?? 0) > 2 ? 'down' : (d.hrv ?? 0) < -2 ? 'up' : 'neutral',
          }),
          statTile({
            label: 'Avg temperature', value: fmtNum(w.temp, 1), unit: '°C',
            delta: d.temp ?? null, tone: Math.abs(d.temp ?? 0) > 0.3 ? 'up' : 'neutral',
          }),
          statTile({
            label: 'Peak stress index', value: fmtNum(w.stress_peak, 2), unit: '/ 1.0',
            delta: d.stress ?? null, tone: (d.stress ?? 0) > 0.05 ? 'up' : (d.stress ?? 0) < -0.05 ? 'down' : 'neutral',
          }),
        ].join('');

        const facts = $('#activity-facts');
        if (facts) {
          facts.innerHTML = `
            <div class="flex-between" style="margin-bottom:8px"><span class="muted">Steps today</span><b class="mono">${fmtNum(stats.steps_today)}</b></div>
            <div class="flex-between" style="margin-bottom:8px"><span class="muted">Active alerts</span>
              <b class="${stats.active_alerts ? 'text-danger' : 'text-ok'}">${stats.active_alerts}</b></div>
            <div class="flex-between"><span class="muted">Min SpO₂ (24h)</span><b class="mono">${fmtNum(w.spo2_min, 0)}%</b></div>
            <div class="flex-between" style="margin-top:8px"><span class="muted">Max temperature</span><b class="mono">${fmtNum(w.temp_max, 1)}°C</b></div>`;
        }
      } else if (grid) {
        grid.innerHTML = emptyState({ icon: icons.activity, title: 'No statistics yet', body: 'Stats appear after the first readings stream in.' });
      }
    };
    await load();
  },
  destroy() {
    rangeHours = 24;
  },
};

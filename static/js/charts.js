/**
 * NeuroLink Wear — dependency-free interactive SVG charts:
 * multi-series line/area with hover crosshair + tooltip, sparklines, bars.
 */
import { esc, fmtTime, fmtDateTime } from './ui.js?v=20260926-2';

function niceTicks(min, max, count = 4) {
  if (min === max) { min -= 1; max += 1; }
  const span = max - min;
  const step = Math.pow(10, Math.floor(Math.log10(span / count)));
  const err = (span / count) / step;
  const mult = err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
  const s = step * mult;
  const start = Math.ceil(min / s) * s;
  const ticks = [];
  for (let v = start; v <= max + 1e-9; v += s) ticks.push(+v.toFixed(6));
  return ticks;
}

const uid = (() => { let i = 0; return () => `g${++i}`; })();

/**
 * lineChart(container, series, opts)
 * series: [{name, color, points:[{t: Date|number, v:number}], area?:bool, dashed?:bool}]
 */
export function lineChart(container, series, opts = {}) {
  const {
    height = 240, unit = '', yDigits = 0, timeFormat = fmtTime,
    min: forceMin, max: forceMax, showLegend = true, fill = true,
    refLines = [],
  } = opts;

  const all = series.flatMap(s => s.points);
  if (!all.length) {
    container.innerHTML = `<div class="empty-state"><p>No data in this range</p></div>`;
    return;
  }
  const W = Math.max(320, container.clientWidth || 640);
  const H = height;
  const padL = 44, padR = 12, padT = 12, padB = 26;
  const iw = W - padL - padR, ih = H - padT - padB;

  const xs = all.map(p => +new Date(p.t));
  let yMin = forceMin !== undefined ? forceMin : Math.min(...all.map(p => p.v));
  let yMax = forceMax !== undefined ? forceMax : Math.max(...all.map(p => p.v));
  const yPad = (yMax - yMin || 1) * 0.12;
  if (forceMin === undefined) yMin -= yPad;
  if (forceMax === undefined) yMax += yPad;

  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const X = (t) => padL + ((+new Date(t) - x0) / (x1 - x0 || 1)) * iw;
  const Y = (v) => padT + ih - ((v - yMin) / (yMax - yMin || 1)) * ih;

  const yTicks = niceTicks(yMin, yMax, 4);
  const nXTicks = Math.min(6, series[0].points.length);
  const xTicks = Array.from({ length: nXTicks }, (_, i) =>
    x0 + (i / Math.max(1, nXTicks - 1)) * (x1 - x0));

  const gridG = yTicks.map(v => `
    <line class="grid-line" x1="${padL}" x2="${W - padR}" y1="${Y(v)}" y2="${Y(v)}"/>
    <text x="${padL - 8}" y="${Y(v) + 3.5}" text-anchor="end">${v.toFixed(yDigits)}</text>`).join('');

  const xAxisG = xTicks.map(t => `
    <text x="${X(t)}" y="${H - 6}" text-anchor="middle">${timeFormat(new Date(t))}</text>`).join('');

  const defsId = uid();
  const seriesG = series.map((s, si) => {
    const pts = s.points.map(p => [X(p.t), Y(p.v)]);
    const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' ');
    const gid = `${defsId}-s${si}`;
    const area = (fill !== false && s.area !== false) ? `
      <path d="${line} L${pts[pts.length - 1][0].toFixed(2)},${(padT + ih).toFixed(2)} L${pts[0][0].toFixed(2)},${(padT + ih).toFixed(2)} Z"
            fill="url(#${gid})" stroke="none"/>
      <defs>
        <linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${s.color}" stop-opacity=".28"/>
          <stop offset="100%" stop-color="${s.color}" stop-opacity="0"/>
        </linearGradient>
      </defs>` : '';
    return `${area}
      <path d="${line}" fill="none" stroke="${s.color}" stroke-width="2.2"
            ${s.dashed ? 'stroke-dasharray="5 5"' : ''} stroke-linecap="round" stroke-linejoin="round"/>`;
  }).join('');

  const refG = refLines.map(r => `
    <line x1="${padL}" x2="${W - padR}" y1="${Y(r.v)}" y2="${Y(r.v)}"
          stroke="${r.color || '#dc2626'}" stroke-width="1.4" stroke-dasharray="6 5" opacity=".75"/>
    ${r.label ? `<text x="${W - padR - 2}" y="${Y(r.v) - 5}" text-anchor="end" fill="${r.color || '#dc2626'}" font-weight="600">${esc(r.label)}</text>` : ''}`).join('');

  const legendHtml = showLegend && series.length > 1 ? `
    <div class="chart-legend">
      ${series.map(s => `<span class="lg-item"><span class="lg-dot" style="background:${s.color}"></span>${esc(s.name)}</span>`).join('')}
    </div>` : '';

  container.innerHTML = `${legendHtml}
    <div class="chart-box" style="position:relative">
      <svg class="chart-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
        ${gridG}
        <line class="axis-line" x1="${padL}" x2="${W - padR}" y1="${padT + ih}" y2="${padT + ih}"/>
        ${refG}
        ${seriesG}
        <line class="xhair" x1="0" x2="0" y1="${padT}" y2="${padT + ih}" stroke="var(--accent)" stroke-width="1" opacity="0"/>
        ${xAxisG}
      </svg>
      <div class="chart-tooltip" style="opacity:0"></div>
    </div>`;

  const svg = container.querySelector('svg');
  const tip = container.querySelector('.chart-tooltip');
  const xhair = container.querySelector('.xhair');

  const onMove = (clientX) => {
    const rect = svg.getBoundingClientRect();
    const relX = ((clientX - rect.left) / rect.width) * W;
    const t = x0 + ((relX - padL) / iw) * (x1 - x0);
    let rows = '';
    let bestX = 0;
    series.forEach(s => {
      let best = s.points[0], bestD = Infinity;
      s.points.forEach(p => {
        const d = Math.abs(+new Date(p.t) - t);
        if (d < bestD) { bestD = d; best = p; }
      });
      bestX = X(best.t);
      rows += `<div class="tt-row"><span class="tt-dot" style="background:${s.color}"></span>
        <span class="muted">${esc(s.name)}</span>
        <b style="margin-left:auto">${best.v.toFixed(yDigits)}${unit}</b></div>`;
    });
    const tLabel = series[0].points.reduce((a, b) =>
      Math.abs(+new Date(b.t) - t) < Math.abs(+new Date(a.t) - t) ? b : a);
    tip.innerHTML = `<div class="tt-title">${fmtDateTime(tLabel.t)}</div>${rows}`;
    tip.style.opacity = '1';
    const px = (bestX / W) * rect.width;
    tip.style.left = `${Math.min(Math.max(px - 60, 4), rect.width - 150)}px`;
    tip.style.top = '6px';
    xhair.setAttribute('x1', bestX);
    xhair.setAttribute('x2', bestX);
    xhair.setAttribute('opacity', '.55');
  };

  svg.addEventListener('mousemove', (e) => onMove(e.clientX));
  svg.addEventListener('touchmove', (e) => { onMove(e.touches[0].clientX); }, { passive: true });
  svg.addEventListener('mouseleave', () => {
    tip.style.opacity = '0';
    xhair.setAttribute('opacity', '0');
  });
}

/** Tiny inline sparkline used in vital cards. */
export function sparkline(values, { color = '#2563eb', height = 46, width = 220, fill = true } = {}) {
  if (!values.length) return '';
  const min = Math.min(...values), max = Math.max(...values);
  const rng = max - min || 1;
  const step = width / Math.max(1, values.length - 1);
  const pts = values.map((v, i) => [i * step, height - 6 - ((v - min) / rng) * (height - 14)]);
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const gid = uid();
  const area = fill ? `
    <path d="${line} L${pts[pts.length - 1][0].toFixed(1)},${height} L0,${height} Z" fill="url(#${gid})" stroke="none"/>
    <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${color}" stop-opacity=".32"/>
      <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
    </linearGradient></defs>` : '';
  return `<svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
    ${area}<path d="${line}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round"/>
  </svg>`;
}

/** Grouped bar chart for daily activity summaries. */
export function barChart(container, labels, series, opts = {}) {
  const { height = 230, unit = '' } = opts;
  const W = Math.max(320, container.clientWidth || 640);
  const H = height;
  const padL = 40, padR = 10, padT = 12, padB = 30;
  const iw = W - padL - padR, ih = H - padT - padB;
  const maxV = Math.max(1, ...series.flatMap(s => s.values)) * 1.12;
  const n = labels.length;
  const groupW = iw / n;
  const barW = Math.min(20, (groupW * 0.62) / series.length);

  const yTicks = niceTicks(0, maxV, 4);
  const gridG = yTicks.map(v => {
    const y = padT + ih - (v / maxV) * ih;
    return `<line class="grid-line" x1="${padL}" x2="${W - padR}" y1="${y}" y2="${y}"/>
      <text x="${padL - 7}" y="${y + 3.5}" text-anchor="end">${v}</text>`;
  }).join('');

  let bars = '';
  labels.forEach((lab, i) => {
    const gx = padL + i * groupW + (groupW - barW * series.length) / 2;
    series.forEach((s, si) => {
      const v = s.values[i] || 0;
      const bh = (v / maxV) * ih;
      bars += `
        <rect x="${(gx + si * barW).toFixed(1)}" y="${(padT + ih - bh).toFixed(1)}"
              width="${(barW - 2.5).toFixed(1)}" height="${Math.max(1.5, bh).toFixed(1)}"
              rx="3" fill="${s.color}" opacity=".9">
          <title>${esc(s.name)} · ${lab}: ${v}${unit}</title>
        </rect>`;
    });
    if (n <= 16 || i % Math.ceil(n / 10) === 0) {
      bars += `<text x="${(padL + i * groupW + groupW / 2).toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(lab)}</text>`;
    }
  });

  const legend = series.length > 1 ? `<div class="chart-legend">
    ${series.map(s => `<span class="lg-item"><span class="lg-dot" style="background:${s.color}"></span>${esc(s.name)}</span>`).join('')}
  </div>` : '';

  container.innerHTML = `${legend}
    <svg class="chart-svg" viewBox="0 0 ${W} ${H}">
      ${gridG}
      <line class="axis-line" x1="${padL}" x2="${W - padR}" y1="${padT + ih}" y2="${padT + ih}"/>
      ${bars}
    </svg>`;
}

/** Horizontal donut used for "activity today" distribution. */
export function donutChart(container, segments, opts = {}) {
  const { size = 150, thickness = 22, centerLabel = '' } = opts;
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  const arcs = segments.filter(s => s.value > 0).map(s => {
    const frac = s.value / total;
    const arc = `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none"
        stroke="${s.color}" stroke-width="${thickness}"
        stroke-dasharray="${(frac * c).toFixed(2)} ${c.toFixed(2)}"
        stroke-dashoffset="${(-offset * c).toFixed(2)}"
        transform="rotate(-90 ${size / 2} ${size / 2})">
        <title>${esc(s.name)}: ${s.value}</title></circle>`;
    offset += frac;
    return arc;
  }).join('');
  container.innerHTML = `
    <div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="flex:0 0 auto">
        <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="var(--surface-3)" stroke-width="${thickness}"/>
        ${arcs}
        <text x="${size / 2}" y="${size / 2}" text-anchor="middle" dominant-baseline="central"
              style="font-size:15px;font-weight:700;fill:var(--text)">${esc(centerLabel)}</text>
      </svg>
      <div style="display:grid;gap:7px">
        ${segments.map(s => `<span class="lg-item"><span class="lg-dot" style="background:${s.color}"></span>${esc(s.name)} · <b>${s.value}</b></span>`).join('')}
      </div>
    </div>`;
}

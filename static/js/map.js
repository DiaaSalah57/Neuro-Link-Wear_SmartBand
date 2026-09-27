/**
 * NeuroLink Wear — map helper (Leaflet + OSM with graceful SVG fallback).
 */
let leafletPromise = null;

function loadScript(src, timeout = 6000) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`script failed: ${src}`));
    document.head.appendChild(s);
    setTimeout(() => reject(new Error(`script timeout: ${src}`)), timeout);
  });
}

function loadLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (leafletPromise) return leafletPromise;
  // Self-hosted first (works offline / behind restrictive networks),
  // CDN only as a last resort.
  leafletPromise = (async () => {
    try {
      await loadScript('/static/vendor/leaflet/leaflet.js');
    } catch {
      await loadScript('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js');
    }
    if (!window.L) throw new Error('Leaflet missing');
    return window.L;
  })();
  return leafletPromise;
}

const fallbackHTML = (lat, lng, label) => `
  <div class="map-fallback">
    <div>
      <div class="pin">📍</div>
      <h4 style="margin:10px 0 4px;color:var(--text)">${label || 'Wearer location'}</h4>
      <div class="gps-pill" style="margin:6px auto;display:inline-flex">${lat.toFixed(5)}, ${lng.toFixed(5)}</div>
      <p class="muted" style="margin-top:8px;font-size:12px">Map tiles could not be loaded (offline?).<br>GPS coordinates are shown above and stay accurate.</p>
    </div>
  </div>`;

/**
 * createMap(containerId, {lat, lng, zoom, markers: [{lat,lng,label,kind}], liveLabel})
 * Returns an object with update(lat, lng) when possible.
 */
export async function createMap(containerId, opts = {}) {
  const el = document.getElementById(containerId);
  if (!el) return { update() {}, destroy() {} };
  const {
    lat = 42.3467, lng = -71.1206, zoom = 15,
    markers = [], liveLabel = 'Margaret Thompson · live position',
  } = opts;

  let L;
  try {
    L = await loadLeaflet();
  } catch {
    el.innerHTML = fallbackHTML(lat, lng, liveLabel);
    return {
      update(a, b) {
        const pill = el.querySelector('.gps-pill');
        if (pill) pill.textContent = `${a.toFixed(5)}, ${b.toFixed(5)}`;
      },
      destroy() {},
    };
  }

  el.innerHTML = '';
  const map = L.map(containerId, { zoomControl: true, attributionControl: true }).setView([lat, lng], zoom);

  // Tile resilience: OSM primary, CARTO secondary, offline notice after that.
  // Markers + GPS coordinates keep working in every case.
  const tileNotice = (msg) => {
    if (el.querySelector('.tile-notice')) return;
    const n2 = document.createElement('div');
    n2.className = 'tile-notice';
    n2.textContent = msg;
    el.appendChild(n2);
  };
  const watchTiles = (layer, onFail) => {
    let errors = 0;
    layer.on('tileerror', () => { if (++errors >= 3) onFail(); });
    return layer;
  };
  const cartoLayer = () => L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  });
  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  });
  watchTiles(osm, () => {
    map.removeLayer(osm);
    watchTiles(cartoLayer().addTo(map), () => {
      tileNotice('Map tiles unavailable — GPS coordinates remain live and accurate');
    });
  }).addTo(map);

  const liveIcon = L.divIcon({
    className: '',
    html: `<div style="position:relative;width:26px;height:26px">
        <span style="position:absolute;inset:0;border-radius:50%;background:rgba(36,20,131,.30);animation:ping 1.8s ease-out infinite"></span>
        <span style="position:absolute;inset:6px;border-radius:50%;background:#241483;border:2.5px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.35)"></span>
      </div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
  const fallIcon = L.divIcon({
    className: '',
    html: `<div style="width:24px;height:24px;border-radius:50%;background:#170c5e;border:2.5px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.4);display:grid;place-items:center;color:#fff;font-size:12px">⚠</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });

  const liveMarker = L.marker([lat, lng], { icon: liveIcon }).addTo(map).bindPopup(liveLabel);
  L.circle([lat, lng], {
    radius: 45, color: '#241483', fillColor: '#241483', fillOpacity: 0.12, weight: 1.5,
  }).addTo(map);

  const alertIcon = L.divIcon({
    className: '',
    html: `<div style="width:22px;height:22px;border-radius:50%;background:#3d3566;border:2.5px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.35)"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });

  const bounds = [[lat, lng]];
  markers.forEach((m) => {
    const mk = L.marker([m.lat, m.lng], { icon: m.kind === 'fall' || m.kind === 'critical' ? fallIcon : alertIcon })
      .addTo(map)
      .bindPopup(`<b>${m.label}</b><br><small>${m.ts || ''}</small>`);
    if (m.focus) mk.openPopup();
    bounds.push([m.lat, m.lng]);
  });
  if (markers.length) map.fitBounds(bounds, { padding: [38, 38], maxZoom: 16 });

  setTimeout(() => map.invalidateSize(), 120);
  window.addEventListener('resize', () => map.invalidateSize());

  return {
    map,
    update(a, b) {
      liveMarker.setLatLng([a, b]);
    },
    destroy() { try { map.remove(); } catch { /* noop */ } },
  };
}

/**
 * NeuroLink Wear — Settings: appearance, account & session, system info.
 */
import { api, auth } from '../api.js?v=20261001-1';
import { $, $$, esc, icons, toast, confirmDialog } from '../ui.js?v=20261001-1';

export default {
  async render(root) {
    const user = auth.user || {};
    root.innerHTML = `
      <div class="page-head">
        <div>
          <h2>Settings</h2>
          <div class="subtitle">Appearance, account security and platform information.</div>
        </div>
      </div>

      <div class="grid cols-2">
        <div class="card">
          <div class="card-head"><h3>${icons.sun} Appearance</h3></div>
          <div class="card-body">
            <div class="flex-between">
              <div>
                <strong style="display:block;font-size:13.5px">Dark mode</strong>
                <small class="muted">Switch between the light clinical theme and the dark night theme.</small>
              </div>
              <input type="checkbox" class="switch" id="set-theme" ${document.documentElement.dataset.theme === 'dark' ? 'checked' : ''}>
            </div>
            <div class="divider"></div>
            <div class="flex-between">
              <div>
                <strong style="display:block;font-size:13.5px">Density</strong>
                <small class="muted">Comfortable spacing for medical review sessions.</small>
              </div>
              <span class="badge neutral">comfortable</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><h3>${icons.users} Account</h3></div>
          <div class="card-body">
            <div class="row" style="align-items:center">
              <span class="avatar lg" style="background:var(--accent)">${esc((user.name || '?').split(' ').map((x) => x[0]).slice(0, 2).join(''))}</span>
              <div>
                <strong style="display:block">${esc(user.name || '')}</strong>
                <small class="muted">${esc(user.email || '')}</small>
              </div>
              <span class="badge ${user.role === 'admin' ? 'purple' : 'neutral'}" style="margin-left:auto">${esc(user.role || '')}</span>
            </div>
            <div class="divider"></div>
            <div class="flex-between" style="margin-bottom:8px">
              <span class="muted">Session</span>
              <b>persisted · expires in 30 days</b>
            </div>
            <div class="flex-between">
              <span class="muted">Permissions</span>
              <b>${user.role === 'admin' ? 'Full platform + team management' : 'Care workflow + dispatch'}</b>
            </div>
            <button class="btn ghost block" id="set-signout" style="margin-top:14px">Sign out of this device</button>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><h3>${icons.shield} Demo quick reference</h3></div>
          <div class="card-body" style="font-size:12.8px;line-height:1.75">
            <p class="muted">This deployment ships pre-seeded with realistic demo data so every flow works instantly:</p>
            <div class="divider"></div>
            <div class="flex-between"><span class="muted">Caregiver login</span><b class="mono">caregiver@neurolink.health · caregiver123</b></div>
            <div class="flex-between" style="margin-top:6px"><span class="muted">Admin login</span><b class="mono">admin@neurolink.health · admin123</b></div>
            <div class="divider"></div>
            <p class="muted">Try the <b>Demo scenario controls</b> on the Live Overview to force fall / stress / fever / low-SpO₂
              events and watch the AI explain and escalate in real time.</p>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><h3>${icons.watch} System</h3></div>
          <div class="card-body" style="font-size:12.8px">
            <div class="flex-between" style="margin-bottom:8px"><span class="muted">Platform</span><b>NeuroLink Wear · Health &amp; Safety Dashboard</b></div>
            <div class="flex-between" style="margin-bottom:8px"><span class="muted">Detection engine</span><b>Rules + Isolation Forest + LSTM ensemble</b></div>
            <div class="flex-between" style="margin-bottom:8px"><span class="muted">Narrative AI</span><b>NeuroLink AI (HF LLM-ready)</b></div>
            <div class="flex-between" style="margin-bottom:8px"><span class="muted">Telemetry path</span><b class="mono">MQTT → pipeline → WebSocket</b></div>
            <div class="flex-between"><span class="muted">Data retention</span><b>30 days rolling</b></div>
            <div class="divider"></div>
            <button class="btn ghost block" id="set-reset-demo">${icons.refresh} Reset live stream (re-sync from device)</button>
          </div>
        </div>
      </div>`;

    $('#set-theme').onchange = (e) => {
      const theme = e.target.checked ? 'dark' : 'light';
      document.documentElement.dataset.theme = theme;
      try { localStorage.setItem('nlw_theme', theme); } catch { /* memory-only */ }
      window.dispatchEvent(new CustomEvent('nlw:theme'));
    };
    $('#set-signout').onclick = () => window.dispatchEvent(new CustomEvent('nlw:logout'));
    $('#set-reset-demo').onclick = async () => {
      try {
        const r = await api.latest();
        toast('success', 'Stream re-synced', `Latest reading ${new Date(r.ts).toLocaleTimeString()} — WebSocket continues live.`);
      } catch (err) {
        toast('error', 'Re-sync failed', err.message);
      }
    };
  },
  destroy() {},
};

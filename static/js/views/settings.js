/**
 * NeuroLink Wear — Settings: appearance, account & session, system info.
 */
import { api, auth } from '../api.js?v=20261001-3';
import { $, $$, esc, icons, toast, confirmDialog } from '../ui.js?v=20261001-3';

export default {
  async render(root) {
    const user = auth.user || {};
    root.innerHTML = `
      <div class="page-head">
        <div>
          <h2>Settings</h2>
          <div class="subtitle">Appearance and account preferences.</div>
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
      </div>`;

    $('#set-theme').onchange = (e) => {
      const theme = e.target.checked ? 'dark' : 'light';
      document.documentElement.dataset.theme = theme;
      try { localStorage.setItem('nlw_theme', theme); } catch { /* memory-only */ }
      window.dispatchEvent(new CustomEvent('nlw:theme'));
    };
    $('#set-signout').onclick = () => window.dispatchEvent(new CustomEvent('nlw:logout'));
  },
  destroy() {},
};

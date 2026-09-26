/**
 * NeuroLink Wear — Caregiver & Device Management:
 * CRUD for emergency contacts, wearable pairing + MQTT config,
 * personalized health thresholds, patient profile and (admin) team users.
 */
import { api, auth } from '../api.js?v=20260926-6';
import {
  $, $$, esc, icons, toast, openModal, closeModal, confirmDialog,
  emptyState, skeletonLines, fmtRelative,
} from '../ui.js?v=20260926-6';

let activeTab = 'contacts';
const isAdmin = () => auth.user && auth.user.role === 'admin';

/* ────────────────────────────────── Contacts ────────────────────────── */
function contactModal(existing = null) {
  openModal({
    title: existing ? 'Edit contact' : 'Add emergency contact',
    body: `
      <div class="form-grid">
        <label class="field"><span>Full name</span>
          <input id="c-name" value="${esc(existing?.name || '')}" placeholder="Jane Smith"></label>
        <label class="field"><span>Relationship</span>
          <input id="c-rel" value="${esc(existing?.relationship || '')}" placeholder="Daughter, physician…"></label>
        <label class="field"><span>Phone</span>
          <input id="c-phone" value="${esc(existing?.phone || '')}" placeholder="+1 (555) 000-0000"></label>
        <label class="field"><span>Email</span>
          <input id="c-email" value="${esc(existing?.email || '')}" placeholder="optional"></label>
        <label class="field"><span>Priority (1 = first)</span>
          <input id="c-prio" type="number" min="1" max="5" value="${existing?.priority || 2}"></label>
        <label class="field"><span>Can receive dispatch</span>
          <select id="c-disp">
            <option value="1" ${existing?.can_dispatch !== 0 ? 'selected' : ''}>Yes</option>
            <option value="0" ${existing?.can_dispatch === 0 ? 'selected' : ''}>No (informational only)</option>
          </select></label>
        <label class="field full"><span>Notes</span>
          <textarea id="c-notes" placeholder="Lives nearby, prefers SMS…">${esc(existing?.notes || '')}</textarea></label>
      </div>`,
    footer: `
      <button class="btn ghost" data-modal-close>Cancel</button>
      <button class="btn primary" id="c-save">${existing ? 'Save changes' : 'Add contact'}</button>`,
  });
  $('#c-save').onclick = async () => {
    const body = {
      name: $('#c-name').value.trim(),
      relationship: $('#c-rel').value.trim(),
      phone: $('#c-phone').value.trim(),
      email: $('#c-email').value.trim(),
      priority: +$('#c-prio').value || 2,
      can_dispatch: $('#c-disp').value === '1',
      notes: $('#c-notes').value.trim(),
    };
    if (!body.name || !body.phone) { toast('warning', 'Name and phone are required'); return; }
    $('#c-save').disabled = true;
    try {
      if (existing) await api.updateContact(existing.id, body);
      else await api.createContact(body);
      closeModal();
      toast('success', existing ? 'Contact updated' : 'Contact added', `${body.name} is on the dispatch list.`);
      renderTab();
    } catch (err) {
      toast('error', 'Save failed', err.message);
      $('#c-save').disabled = false;
    }
  };
}

async function renderContacts(box) {
  if (!box || !box.isConnected) return;
  box.innerHTML = `<div class="card card-pad">${skeletonLines(5)}</div>`;
  let contacts;
  try {
    contacts = await api.contacts();
  } catch (err) {
    box.innerHTML = emptyState({ icon: icons.users, title: 'Could not load contacts', body: esc(err.message) });
    return;
  }
  if (!contacts.length) {
    box.innerHTML = emptyState({
      icon: icons.users, title: 'No emergency contacts saved',
      body: 'Add at least one contact so emergency dispatch has somewhere to go.',
      action: '<button class="btn primary sm" id="empty-add-contact">Add first contact</button>',
    });
    $('#empty-add-contact').onclick = () => contactModal();
    return;
  }
  box.innerHTML = `
    <div class="flex-between" style="margin-bottom:14px">
      <div class="muted" style="font-size:12.5px">${contacts.length} saved · priority order controls the dispatch sequence</div>
      <button class="btn primary sm" id="add-contact">${icons.plus} Add contact</button>
    </div>
    <div class="card table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>Priority</th><th>Name</th><th>Relationship</th><th>Phone</th><th>Dispatch</th><th style="text-align:right">Actions</th>
        </tr></thead>
        <tbody>
          ${contacts.map((c) => `
            <tr data-id="${c.id}">
              <td><span class="badge ${c.priority === 1 ? 'high' : 'neutral'}">P${c.priority}</span></td>
              <td><strong>${esc(c.name)}</strong>${c.notes ? `<div class="muted" style="font-size:11.5px">${esc(c.notes)}</div>` : ''}</td>
              <td>${esc(c.relationship)}</td>
              <td class="mono">${esc(c.phone)}</td>
              <td>${c.can_dispatch ? '<span class="badge ok">enabled</span>' : '<span class="badge neutral">off</span>'}</td>
              <td><div class="actions">
                <button class="icon-btn" data-edit title="Edit">${icons.edit}</button>
                <button class="icon-btn" data-del title="Delete">${icons.trash}</button>
              </div></td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  $('#add-contact').onclick = () => contactModal();
  $$('tr[data-id]').forEach((tr) => {
    const c = contacts.find((x) => x.id === +tr.dataset.id);
    tr.querySelector('[data-edit]').onclick = () => contactModal(c);
    tr.querySelector('[data-del]').onclick = async () => {
      if (await confirmDialog('Delete contact?', `<b>${esc(c.name)}</b> will be removed from the emergency dispatch list.`, 'Delete')) {
        // Optimistic removal — UI updates instantly, rolls back on error
        tr.style.opacity = '.35';
        try {
          await api.deleteContact(c.id);
          toast('success', 'Contact deleted', `${c.name} removed from the dispatch list.`);
          renderTab();
        } catch (err) {
          tr.style.opacity = '1';
          toast('error', 'Delete failed — change rolled back', err.message);
        }
      }
    };
  });
}

/* ─────────────────────────────────── Devices ────────────────────────── */
function deviceModal(existing = null) {
  openModal({
    title: existing ? 'Edit device & broker config' : 'Pair a new wearable',
    wide: true,
    body: `
      <div class="form-grid">
        <label class="field"><span>Device name</span>
          <input id="d-name" value="${esc(existing?.name || '')}" placeholder="Margaret's NeuroLink Band"></label>
        <label class="field"><span>Model</span>
          <input id="d-model" value="${esc(existing?.model || 'NeuroLink Band NL-200')}"></label>
        <label class="field"><span>Serial number</span>
          <input id="d-serial" value="${esc(existing?.serial || '')}" placeholder="NLW-0000-X"></label>
        <label class="field"><span>Firmware</span>
          <input id="d-fw" value="${esc(existing?.firmware || '2.4.1')}"></label>
      </div>
      <div class="divider"></div>
      <div class="row" style="margin-bottom:10px">
        <strong style="font-size:13px">${icons.wifi} MQTT / Broker pairing</strong>
        <span class="badge neutral">protocol</span>
      </div>
      <div class="form-grid">
        <label class="field"><span>Protocol</span>
          <select id="d-proto">
            <option value="mqtt" ${existing?.protocol !== 'http' ? 'selected' : ''}>MQTT</option>
            <option value="http" ${existing?.protocol === 'http' ? 'selected' : ''}>HTTPS webhook</option>
          </select></label>
        <label class="field"><span>Broker host</span>
          <input id="d-host" value="${esc(existing?.mqtt_host || 'broker.hivemq.com')}"></label>
        <label class="field"><span>Broker port</span>
          <input id="d-port" type="number" value="${existing?.mqtt_port || 1883}"></label>
        <label class="field"><span>Topic</span>
          <input id="d-topic" value="${esc(existing?.mqtt_topic || 'neurolink/sensors')}"></label>
        <label class="field"><span>Username</span>
          <input id="d-user" value="${esc(existing?.mqtt_username || '')}" placeholder="optional"></label>
        <label class="field"><span>Password</span>
          <input id="d-pass" type="password" value="${existing?.mqtt_password ? '••••••••' : ''}" placeholder="optional"></label>
        <label class="field full">
          <span style="display:flex;align-items:center;gap:8px">
            <input type="checkbox" id="d-tls" ${existing?.mqtt_tls !== 0 ? 'checked' : ''} style="width:16px;height:16px;accent-color:var(--accent)">
            Use TLS encryption for the broker connection
          </span>
        </label>
      </div>`,
    footer: `
      ${existing ? '<button class="btn ghost" id="d-test">' + icons.wifi + ' Test connection</button>' : ''}
      <button class="btn ghost" data-modal-close>Cancel</button>
      <button class="btn primary" id="d-save">${existing ? 'Save configuration' : 'Pair device'}</button>`,
  });
  const testBtn = $('#d-test');
  if (testBtn) {
    testBtn.onclick = async () => {
      testBtn.disabled = true;
      testBtn.innerHTML = `${icons.refresh} Testing…`;
      try {
        const res = await api.testDevice(existing.id);
        if (res.ok) toast('success', 'Broker reachable', res.message);
        else toast('error', `Broker test failed (${res.stage || 'unknown'})`, res.message);
      } catch (err) {
        toast('error', 'Connection test failed', err.message);
      } finally {
        testBtn.disabled = false;
        testBtn.innerHTML = `${icons.wifi} Test connection`;
      }
    };
  }
  $('#d-save').onclick = async () => {
    const body = {
      name: $('#d-name').value.trim(),
      model: $('#d-model').value.trim(),
      serial: $('#d-serial').value.trim(),
      firmware: $('#d-fw').value.trim(),
      status: 'paired',
      protocol: $('#d-proto').value,
      mqtt_host: $('#d-host').value.trim(),
      mqtt_port: +$('#d-port').value || 1883,
      mqtt_topic: $('#d-topic').value.trim(),
      mqtt_username: $('#d-user').value.trim(),
      mqtt_password: $('#d-pass').value === '••••••••' ? (existing?.mqtt_password || '') : $('#d-pass').value,
      mqtt_tls: $('#d-tls').checked,
      patient_id: 1,
    };
    if (!body.name || !body.serial) { toast('warning', 'Name and serial are required'); return; }
    $('#d-save').disabled = true;
    try {
      if (existing) await api.updateDevice(existing.id, body);
      else await api.createDevice(body);
      closeModal();
      toast('success', existing ? 'Device configuration saved' : 'Device paired', `${body.name} is linked to Margaret's profile.`);
      renderTab();
    } catch (err) {
      toast('error', 'Save failed', err.message);
      $('#d-save').disabled = false;
    }
  };
}

async function renderDevices(box) {
  if (!box || !box.isConnected) return;
  box.innerHTML = `<div class="card card-pad">${skeletonLines(5)}</div>`;
  const devices = await api.devices().catch(() => []);
  box.innerHTML = `
    <div class="flex-between" style="margin-bottom:14px">
      <div class="muted" style="font-size:12.5px">Wearables stream through MQTT into the NeuroLink pipeline — pairing config lives here.</div>
      ${isAdmin() ? `<button class="btn primary sm" id="add-device">${icons.plus} Pair device</button>` : '<span class="badge purple">read-only · admin manages devices</span>'}
    </div>
    <div class="grid cols-2">
      ${devices.map((d) => `
        <div class="card">
          <div class="card-pad">
            <div class="flex-between">
              <div class="row">
                <div class="vital-icon" style="background:var(--accent-soft);color:var(--accent)">${icons.watch}</div>
                <div>
                  <strong>${esc(d.name)}</strong>
                  <div class="muted" style="font-size:11.5px">${esc(d.model)} · SN ${esc(d.serial)} · FW ${esc(d.firmware)}</div>
                </div>
              </div>
              <span class="badge ${d.online ? 'ok' : d.status === 'paired' ? 'medium' : 'neutral'}">${d.online ? 'online' : esc(d.status)}</span>
            </div>
            <div class="divider"></div>
            <div class="flex-between" style="margin-bottom:6px">
              <span class="muted">Battery</span><b class="mono">${d.battery}%${d.charging ? ' ⚡ charging' : ''}</b>
            </div>
            <div class="meter" style="margin-bottom:12px"><i style="width:${d.battery}%;background:${d.battery < 20 ? 'var(--danger)' : 'var(--ok)'}"></i></div>
            <div class="flex-between" style="margin-bottom:6px">
              <span class="muted">Broker</span><b class="mono" style="font-size:11.5px">${esc(d.mqtt_host)}:${d.mqtt_port}${d.mqtt_tls ? ' 🔒' : ''}</b>
            </div>
            <div class="flex-between" style="margin-bottom:6px">
              <span class="muted">${d.mqtt_tls ? 'TLS MQTT URL' : 'MQTT URL'}</span>
              <b class="mono" style="font-size:11px">${d.mqtt_tls ? 'mqtts' : 'mqtt'}://${esc(d.mqtt_host)}:${d.mqtt_port}</b>
            </div>
            ${d.mqtt_tls ? `
            <div class="flex-between" style="margin-bottom:6px">
              <span class="muted">TLS Websocket URL</span>
              <b class="mono" style="font-size:11px">wss://${esc(d.mqtt_host)}:8884/mqtt</b>
            </div>` : ''}
            <div class="flex-between" style="margin-bottom:6px">
              <span class="muted">Topic</span><b class="mono" style="font-size:11.5px">${esc(d.mqtt_topic)}</b>
            </div>
            <div class="flex-between">
              <span class="muted">Last seen</span><b>${fmtRelative(d.last_seen)}</b>
            </div>
            ${isAdmin() ? `
            <div class="row" style="margin-top:13px">
              <button class="btn ghost sm" data-test="${d.id}">${icons.wifi} Test</button>
              <button class="btn ghost sm" data-editd="${d.id}">${icons.edit} Edit config</button>
              <button class="btn ghost sm" data-deld="${d.id}">${icons.trash} Remove</button>
            </div>` : ''}
          </div>
        </div>`).join('')}
    </div>`;

  const addBtn = $('#add-device');
  if (addBtn) addBtn.onclick = () => deviceModal();
  $$('[data-editd]').forEach((b) => b.onclick = () => deviceModal(devices.find((d) => d.id === +b.dataset.editd)));
  $$('[data-test]').forEach((b) => {
    b.onclick = async () => {
      b.disabled = true;
      try {
        const res = await api.testDevice(+b.dataset.test);
        if (res.ok) toast('success', 'Broker reachable', res.message);
        else toast('error', `Broker test failed (${res.stage || 'unknown'})`, res.message);
      } catch (err) {
        toast('error', 'Test failed', err.message);
      } finally {
        b.disabled = false;
      }
    };
  });
  $$('[data-deld]').forEach((b) => {
    b.onclick = async () => {
      const d = devices.find((x) => x.id === +b.dataset.deld);
      if (await confirmDialog('Remove device?', `<b>${esc(d.name)}</b> will be unpaired and its MQTT config deleted.`, 'Remove')) {
        await api.deleteDevice(d.id).then(() => {
          toast('success', 'Device removed');
          renderTab();
        }).catch((e) => toast('error', 'Remove failed', e.message));
      }
    };
  });
}

/* ────────────────────────────────── Thresholds ──────────────────────── */
async function renderThresholds(box) {
  if (!box || !box.isConnected) return;
  box.innerHTML = `<div class="card card-pad">${skeletonLines(6)}</div>`;
  const t = await api.thresholds().catch(() => null);
  if (!t) {
    box.innerHTML = emptyState({ icon: icons.settings, title: 'Thresholds unavailable', body: 'Could not load alert thresholds.' });
    return;
  }
  box.innerHTML = `
    <div class="card">
      <div class="card-head">
        <h3>${icons.settings} Personalized Health Alert Thresholds</h3>
        <button class="btn ghost sm" id="th-reset">Reset to recommended</button>
      </div>
      <div class="card-body">
        <p class="muted" style="font-size:12.5px;margin-bottom:12px">
          Alerts fire the moment a live reading crosses these limits. Values are tailored to Margaret's clinical profile
          (hypertension, mild COPD). Changes take effect on the next reading — typically within 2 seconds.
        </p>
        <div class="threshold-row">
          <div class="th-label"><strong>Heart rate — safe window</strong><small>tachycardia / bradycardia alerts</small></div>
          <div class="range-pair">
            <input type="number" id="th-hr-low" value="${t.hr_low}" min="30" max="80"> <span class="muted">to</span>
            <input type="number" id="th-hr-high" value="${t.hr_high}" min="80" max="200"> <span class="muted">bpm</span>
          </div>
          <span class="badge neutral">bpm</span>
        </div>
        <div class="threshold-row">
          <div class="th-label"><strong>Blood oxygen (SpO₂) minimum</strong><small>low-oxygen alerts</small></div>
          <div class="range-pair"><input type="number" id="th-spo2" value="${t.spo2_low}" min="80" max="99" step="0.5"> <span class="muted">%</span></div>
          <span class="badge high">critical if −3%</span>
        </div>
        <div class="threshold-row">
          <div class="th-label"><strong>Temperature — fever ceiling</strong><small>fever alerts</small></div>
          <div class="range-pair"><input type="number" id="th-temp-high" value="${t.temp_high}" min="36.5" max="40" step="0.1"> <span class="muted">°C</span></div>
          <span class="badge medium">fever</span>
        </div>
        <div class="threshold-row">
          <div class="th-label"><strong>Temperature — low floor</strong><small>hypothermia watch</small></div>
          <div class="range-pair"><input type="number" id="th-temp-low" value="${t.temp_low}" min="32" max="36.5" step="0.1"> <span class="muted">°C</span></div>
          <span class="badge neutral">low</span>
        </div>
        <div class="threshold-row">
          <div class="th-label"><strong>Stress index ceiling</strong><small>from GSR + HRV composite score</small></div>
          <div class="range-pair"><input type="number" id="th-stress" value="${t.stress_high}" min="0.2" max="0.95" step="0.05"> <span class="muted">/ 1.0</span></div>
          <span class="badge purple">stress</span>
        </div>
        <div class="threshold-row">
          <div class="th-label"><strong>HRV fatigue floor</strong><small>fatigue / overtraining alerts</small></div>
          <div class="range-pair"><input type="number" id="th-hrv" value="${t.hrv_low}" min="5" max="50"> <span class="muted">ms</span></div>
          <span class="badge neutral">fatigue</span>
        </div>
        <div class="threshold-row">
          <div class="th-label"><strong>Fall detection impact</strong><small>accelerometer threshold</small></div>
          <div class="range-pair"><input type="number" id="th-fall" value="${t.fall_accel}" min="1.5" max="5" step="0.1"> <span class="muted">g</span></div>
          <input type="checkbox" class="switch" id="th-fall-enabled" ${t.fall_enabled ? 'checked' : ''} title="Enable fall detection">
        </div>
        <div class="threshold-row">
          <div class="th-label"><strong>Inactivity alert</strong><small>no movement during waking hours</small></div>
          <div class="range-pair"><input type="number" id="th-inact" value="${t.inactivity_minutes}" min="15" max="360"> <span class="muted">min</span></div>
          <span class="badge medium">monitor</span>
        </div>
        <div class="row" style="margin-top:16px;justify-content:flex-end">
          <span class="muted" id="th-saved" style="font-size:12px"></span>
          <button class="btn primary" id="th-save">${icons.check} Save thresholds</button>
        </div>
      </div>
    </div>`;

  $('#th-reset').onclick = () => {
    $('#th-hr-low').value = 52; $('#th-hr-high').value = 112; $('#th-spo2').value = 92;
    $('#th-temp-high').value = 37.8; $('#th-temp-low').value = 35.5; $('#th-stress').value = 0.60;
    $('#th-hrv').value = 20; $('#th-fall').value = 2.8; $('#th-inact').value = 90;
    $('#th-fall-enabled').checked = true;
    toast('info', 'Reset to recommended values', 'Press Save to apply.');
  };
  $('#th-save').onclick = async () => {
    const saveBtn = $('#th-save');
    const body = {
      hr_low: +$('#th-hr-low').value, hr_high: +$('#th-hr-high').value,
      spo2_low: +$('#th-spo2').value, temp_high: +$('#th-temp-high').value,
      temp_low: +$('#th-temp-low').value, stress_high: +$('#th-stress').value,
      hrv_low: +$('#th-hrv').value, gsr_high: t.gsr_high,
      fall_accel: +$('#th-fall').value, fall_enabled: $('#th-fall-enabled').checked,
      inactivity_minutes: +$('#th-inact').value,
    };
    saveBtn.disabled = true;
    try {
      await api.updateThresholds(body);
      $('#th-saved').textContent = `Saved · thresholds updated ${new Date().toLocaleTimeString()}`;
      toast('success', 'Thresholds saved', 'The detection engine is already using the new limits.');
    } catch (err) {
      toast('error', 'Save failed', err.message);
    } finally {
      saveBtn.disabled = false;
    }
  };
}

/* ──────────────────────────────────── Users ─────────────────────────── */
function userModal(existing = null) {
  openModal({
    title: existing ? 'Edit team member' : 'Add team member',
    body: `
      <div class="form-grid">
        <label class="field"><span>Full name</span><input id="u-name" value="${esc(existing?.name || '')}"></label>
        <label class="field"><span>Email</span><input id="u-email" type="email" value="${esc(existing?.email || '')}" ${existing ? 'disabled' : ''}></label>
        <label class="field"><span>Role</span>
          <select id="u-role">
            <option value="caregiver" ${existing?.role !== 'admin' ? 'selected' : ''}>Caregiver</option>
            <option value="admin" ${existing?.role === 'admin' ? 'selected' : ''}>Admin</option>
          </select></label>
        <label class="field"><span>Phone</span><input id="u-phone" value="${esc(existing?.phone || '')}"></label>
        <label class="field full"><span>${existing ? 'New password (leave blank to keep)' : 'Password (min 6 chars)'}</span>
          <input id="u-pass" type="password" placeholder="••••••"></label>
      </div>`,
    footer: `
      <button class="btn ghost" data-modal-close>Cancel</button>
      <button class="btn primary" id="u-save">${existing ? 'Save' : 'Create user'}</button>`,
  });
  $('#u-save').onclick = async () => {
    const pass = $('#u-pass').value;
    $('#u-save').disabled = true;
    try {
      if (existing) {
        await api.updateUser(existing.id, {
          name: $('#u-name').value.trim(), role: $('#u-role').value,
          phone: $('#u-phone').value.trim(), password: pass || null,
        });
      } else {
        await api.createUser({
          name: $('#u-name').value.trim(), email: $('#u-email').value.trim(),
          role: $('#u-role').value, phone: $('#u-phone').value.trim(), password: pass,
        });
      }
      closeModal();
      toast('success', existing ? 'User updated' : 'User created');
      renderTab();
    } catch (err) {
      toast('error', 'Save failed', err.message);
      $('#u-save').disabled = false;
    }
  };
}

async function renderUsers(box) {
  if (!box || !box.isConnected) return;
  if (!isAdmin()) {
    box.innerHTML = emptyState({ icon: icons.users, title: 'Admins only', body: 'Team management is restricted to administrator accounts.' });
    return;
  }
  box.innerHTML = `<div class="card card-pad">${skeletonLines(4)}</div>`;
  const users = await api.users().catch(() => []);
  box.innerHTML = `
    <div class="flex-between" style="margin-bottom:14px">
      <div class="muted" style="font-size:12.5px">Role-based access: admins manage the platform, caregivers manage the care workflow.</div>
      <button class="btn primary sm" id="add-user">${icons.plus} Add team member</button>
    </div>
    <div class="card table-wrap">
      <table class="data-table">
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Phone</th><th style="text-align:right">Actions</th></tr></thead>
        <tbody>
          ${users.map((u) => `
            <tr data-uid="${u.id}">
              <td><strong>${esc(u.name)}</strong></td>
              <td class="muted">${esc(u.email)}</td>
              <td><span class="badge ${u.role === 'admin' ? 'purple' : 'neutral'}">${esc(u.role)}</span></td>
              <td class="mono">${esc(u.phone || '—')}</td>
              <td><div class="actions">
                <button class="icon-btn" data-uedit>${icons.edit}</button>
                <button class="icon-btn" data-udel>${icons.trash}</button>
              </div></td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  $('#add-user').onclick = () => userModal();
  $$('tr[data-uid]').forEach((tr) => {
    const u = users.find((x) => x.id === +tr.dataset.uid);
    tr.querySelector('[data-uedit]').onclick = () => userModal(u);
    tr.querySelector('[data-udel]').onclick = async () => {
      if (await confirmDialog('Delete user?', `<b>${esc(u.name)}</b> will lose dashboard access immediately.`, 'Delete')) {
        api.deleteUser(u.id).then(() => {
          toast('success', 'User deleted');
          renderTab();
        }).catch((e) => toast('error', 'Delete refused', e.message));
      }
    };
  });
}

/* ──────────────────────────────────── Patient ──────────────────────── */
async function renderPatient(box) {
  if (!box || !box.isConnected) return;
  const p = await api.patient().catch(() => null);
  if (!p) { box.innerHTML = emptyState({ icon: icons.users, title: 'Profile unavailable' }); return; }
  box.innerHTML = `
    <div class="card">
      <div class="card-head"><h3>${icons.users} Wearer Profile</h3>
        ${isAdmin() ? '' : '<span class="badge purple">read-only · admin edits profile</span>'}
      </div>
      <div class="card-body">
        <div class="row" style="align-items:center;margin-bottom:16px">
          <span class="avatar lg" style="background:${esc(p.avatar_color)}">MT</span>
          <div>
            <strong style="font-size:17px">${esc(p.name)}</strong>
            <div class="muted">${p.age} · ${esc(p.gender)} · ${esc(p.room)}</div>
          </div>
        </div>
        <div class="form-grid">
          <label class="field"><span>Full name</span><input id="p-name" value="${esc(p.name)}" ${isAdmin() ? '' : 'disabled'}></label>
          <label class="field"><span>Age</span><input id="p-age" type="number" value="${p.age}" ${isAdmin() ? '' : 'disabled'}></label>
          <label class="field full"><span>Address</span><input id="p-addr" value="${esc(p.address)}" ${isAdmin() ? '' : 'disabled'}></label>
          <label class="field full"><span>Medical conditions</span><textarea id="p-cond" ${isAdmin() ? '' : 'disabled'}>${esc(p.conditions)}</textarea></label>
          <label class="field full"><span>Medications</span><textarea id="p-meds" ${isAdmin() ? '' : 'disabled'}>${esc(p.medications)}</textarea></label>
          <label class="field full"><span>Emergency note</span><textarea id="p-note" ${isAdmin() ? '' : 'disabled'}>${esc(p.emergency_note)}</textarea></label>
        </div>
        ${isAdmin() ? '<div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn primary" id="p-save">' + icons.check + ' Save profile</button></div>' : ''}
      </div>
    </div>`;
  const save = $('#p-save');
  if (save) {
    save.onclick = async () => {
      save.disabled = true;
      try {
        await api.updatePatient({
          name: $('#p-name').value.trim(), age: +$('#p-age').value,
          address: $('#p-addr').value.trim(), conditions: $('#p-cond').value.trim(),
          medications: $('#p-meds').value.trim(), emergency_note: $('#p-note').value.trim(),
        });
        toast('success', 'Profile updated');
      } catch (err) {
        toast('error', 'Save failed', err.message);
      } finally {
        save.disabled = false;
      }
    };
  }
}

/* ─────────────────────────────────── router ────────────────────────── */
async function renderTab() {
  const box = $('#mgmt-tab-content');
  if (!box) return;
  if (activeTab === 'contacts') await renderContacts(box);
  else if (activeTab === 'devices') await renderDevices(box);
  else if (activeTab === 'thresholds') await renderThresholds(box);
  else if (activeTab === 'team') await renderUsers(box);
  else if (activeTab === 'patient') await renderPatient(box);
}

export default {
  async render(root, ctx) {
    const params = ctx.params || {};
    if (params.tab && ['contacts', 'devices', 'thresholds', 'team', 'patient'].includes(params.tab)) {
      activeTab = params.tab;
    }
    root.innerHTML = `
      <div class="page-head">
        <div>
          <h2>Caregiver &amp; Device Management</h2>
          <div class="subtitle">Emergency contacts, wearable pairing with MQTT broker configuration, personalized alert thresholds and the care team.</div>
        </div>
      </div>
      <div class="tabs" id="mgmt-tabs">
        <button class="tab-btn ${activeTab === 'contacts' ? 'active' : ''}" data-tab="contacts">Emergency contacts</button>
        <button class="tab-btn ${activeTab === 'devices' ? 'active' : ''}" data-tab="devices">Devices &amp; MQTT</button>
        <button class="tab-btn ${activeTab === 'thresholds' ? 'active' : ''}" data-tab="thresholds">Alert thresholds</button>
        <button class="tab-btn ${activeTab === 'patient' ? 'active' : ''}" data-tab="patient">Wearer profile</button>
        <button class="tab-btn ${activeTab === 'team' ? 'active' : ''}" data-tab="team">Care team ${isAdmin() ? '' : '🔒'}</button>
      </div>
      <div id="mgmt-tab-content"></div>`;

    $$('#mgmt-tabs .tab-btn').forEach((b) => {
      b.onclick = () => {
        activeTab = b.dataset.tab;
        $$('#mgmt-tabs .tab-btn').forEach((x) => x.classList.toggle('active', x === b));
        renderTab();
      };
    });
    await renderTab();
  },
  destroy() {},
};

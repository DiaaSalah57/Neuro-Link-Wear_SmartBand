/**
 * NeuroLink Wear — login view.
 */
import { api, auth } from '../api.js?v=20260927-2';
import { $, toast } from '../ui.js?v=20260927-2';

export default {
  render() {
    const screen = $('#login-screen');
    screen.classList.remove('hidden');
    $('#app-shell').classList.add('hidden');

    const form = $('#login-form');
    const errBox = $('#login-error');
    const submit = $('#login-submit');

    document.querySelectorAll('.demo-chip').forEach((chip) => {
      chip.onclick = () => {
        $('#login-email').value = chip.dataset.email;
        $('#login-password').value = chip.dataset.pw;
        $('#login-email').focus();
      };
    });

    form.onsubmit = async (e) => {
      e.preventDefault();
      errBox.classList.add('hidden');
      submit.classList.add('loading');
      submit.textContent = 'Signing in…';
      try {
        const res = await api.login($('#login-email').value.trim(), $('#login-password').value);
        if (!res || !res.token || !res.user) {
          throw new Error('Unexpected server response — please retry');
        }
        auth.set(res.token, res.user);
        toast('success', `Welcome, ${res.user.name.split(' ')[0]}`, 'Secure session started — it will persist for 30 days.');
        window.dispatchEvent(new CustomEvent('nlw:login'));
      } catch (err) {
        if (err && err.status === 0) {
          errBox.textContent = 'Cannot reach the dashboard server — it may be restarting. Please wait a moment and try again.';
        } else {
          errBox.textContent = err.message || 'Sign-in failed';
        }
        errBox.classList.remove('hidden');
      } finally {
        submit.classList.remove('loading');
        submit.textContent = 'Sign in';
      }
    };
  },
};

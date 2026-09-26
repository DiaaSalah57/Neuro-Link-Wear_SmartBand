/**
 * NeuroLink Wear — tiny reactive store for live telemetry + app state.
 */
const subs = new Set();

export const store = {
  telemetry: null,     // latest vitals reading
  device: null,        // device status
  patient: null,
  user: null,
  activeAlerts: 0,
  spark: { heart_rate: [], spo2: [], temperature: [], gsr: [], hrv: [], stress_score: [] },
  sparkMax: 60,

  set(key, value) {
    this[key] = value;
    this.notify(key);
  },

  pushSpark(reading) {
    for (const k of Object.keys(this.spark)) {
      const arr = this.spark[k];
      arr.push(reading[k] ?? 0);
      if (arr.length > this.sparkMax) arr.shift();
    }
    this.notify('spark');
  },

  notify(what) {
    subs.forEach((fn) => {
      try { fn(what, this); } catch (e) { console.error('[store]', e); }
    });
  },

  subscribe(fn) {
    subs.add(fn);
    return () => subs.delete(fn);
  },
};

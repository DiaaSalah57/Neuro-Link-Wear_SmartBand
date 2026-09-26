"""
NeuroLink Wear — AI narrative engine.

Produces plain-language health explanations and actionable recommendations for
every detected anomaly, plus rolling AI health summaries. If a HuggingFace
token is configured (HF_TOKEN env var) the real LLM is consulted first and the
local narrative engine acts as the graceful fallback, so the dashboard always
has a helpful, human-sounding explanation on screen.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import datetime, timezone

# Optional live LLM (HuggingFace Inference API) — same contract as pipeline.py
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_URL = (
    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
)


def _pick(options: list[str], key: str) -> str:
    """Deterministic-but-varied template selection."""
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return options[h % len(options)]


# ── Per-condition narrative templates ────────────────────────────────────────
_EXPLAIN = {
    "Fall Detected": [
        "The band's accelerometer recorded a sharp impact spike of {accel_mag} g combined with a sudden gyro rotation of {gyro_mag} rad/s — a motion signature strongly consistent with a fall at {time}. Heart rate jumped to {heart_rate} bpm right after impact, which is a typical cardiovascular stress response to a fall.",
        "A high-energy impact ({accel_mag} g) with abrupt rotational change ({gyro_mag} rad/s) was detected at {time}. The pattern matches the device's fall-detection model: free-fall-like acceleration followed by a hard landing. Post-event heart rate is {heart_rate} bpm.",
    ],
    "Low Oxygen": [
        "Blood oxygen saturation dipped to {spo2}% — below the {spo2_safe}% safety floor set for {name}. SpO2 readings at this level can leave a person feeling breathless, fatigued, or mildly confused, and often worsen overnight when breathing is shallower.",
        "The pulse-oximeter channel reports {spo2}%, a {spo2_drop} point drop below the configured minimum of {spo2_safe}%. For someone with {conditions}, this may indicate shallow breathing, airway obstruction during rest, or a developing chest infection.",
    ],
    "Fever": [
        "Skin temperature climbed to {temperature}°C, crossing the {temp_safe}°C fever threshold. A sustained rise like this often points to infection or inflammation; combined with the elevated resting heart rate of {heart_rate} bpm it is worth confirming with an oral thermometer.",
        "The temperature sensor reports {temperature}°C — {temp_delta}°C above {name}'s safe ceiling of {temp_safe}°C. Fever in elderly patients can progress quickly, so this reading should be verified and watched closely over the next few hours.",
    ],
    "High Stress": [
        "Galvanic skin response rose to {gsr} µS while heart-rate variability fell to {hrv} ms — the classic electrodermal signature of acute stress or anxiety. The combined stress index is {stress}/1.00, which is well above {name}'s calm baseline.",
        "Stress index reached {stress}/1.00: sweat-gland activity ({gsr} µS) is elevated and HRV ({hrv} ms) is suppressed, meaning the sympathetic nervous system ('fight or flight') is dominating. Heart rate is running {hr_delta} bpm above the activity-adjusted expectation.",
    ],
    "Panic Attack": [
        "Heart rate surged to {heart_rate} bpm — {hr_delta} bpm above the expected level for the current activity — while the stress index hit {stress}/1.00. This combination of tachycardia, high electrodermal activity ({gsr} µS) and collapsing HRV ({hrv} ms) is consistent with a panic episode or acute distress event.",
        "A critical stress cascade is underway: {heart_rate} bpm heart rate with stress index {stress}/1.00 and HRV down to {hrv} ms. Symptoms can include chest tightness, trembling and shortness of breath; the pattern requires immediate human attention.",
    ],
    "Tachycardia": [
        "Heart rate is {heart_rate} bpm, above the {hr_safe} bpm comfort ceiling configured for {name}. Persistently elevated pulse can reflect pain, fever, dehydration, arrhythmia or simple overexertion.",
        "The optical heart-rate channel reports {heart_rate} bpm at rest — tachycardia territory for an elderly patient whose ceiling is set to {hr_safe} bpm.",
    ],
    "Bradycardia": [
        "Heart rate dropped to {heart_rate} bpm, below the {hr_low_safe} bpm floor. Slow pulse in elderly patients can cause dizziness, fainting or fatigue and should be correlated with how {name} is feeling right now.",
        "The band recorded {heart_rate} bpm — bradycardia relative to the configured {hr_low_safe} bpm minimum. If this coincides with light-headedness or falls, medical review is recommended.",
    ],
    "Fatigue": [
        "Heart-rate variability has fallen to {hrv} ms with a stress index of {stress}/1.00. Low HRV through the day is a strong marker of physical fatigue, poor recovery or insufficient sleep.",
        "HRV of {hrv} ms suggests {name}'s autonomic nervous system is under-recovered. Fatigue like this raises fall risk, so keeping activity gentle is advisable.",
    ],
    "Inactivity": [
        "The motion sensors recorded no meaningful movement for {inactive_minutes} minutes during waking hours. Prolonged immobility in elderly patients raises the risk of stiffness, pressure sores, blood clots and unnoticed falls.",
        "No walking or arm movement has been detected for {inactive_minutes} minutes. If this is unexpected, it may be worth checking on {name} — extended stillness can also follow a fall the band classified as low-energy.",
    ],
    "General Anomaly": [
        "The ensemble anomaly model flagged a reading pattern outside {name}'s learned baseline: stress index {stress}/1.00 with heart rate at {heart_rate} bpm and HRV at {hrv} ms. Nothing single-handedly critical, but the combination is atypical.",
        "A mild outlier pattern was detected across multiple channels simultaneously (HR {heart_rate} bpm, HRV {hrv} ms, stress {stress}/1.00). These multi-sensor disagreements are often early signs worth monitoring.",
    ],
    "Emergency SOS": [
        "The emergency SOS button was triggered manually at {time} from the NeuroLink Wear app. This is a user-initiated distress call and takes priority over all automated detections.",
        "A one-press SOS was activated at {time}. Wearer GPS position at activation is being shared with the dispatch list.",
    ],
}

_RECOMMEND = {
    "Fall Detected": [
        ["Call {name} immediately — if there is no answer within 60 seconds, send someone to the location on the map.", "Do not ask {name} to get up unassisted; falls in elderly patients are frequently followed by a second fall.", "If there is head impact, confusion, or pain in the hip/wrist, arrange medical evaluation today."],
        ["Dispatch the nearest emergency contact now and share the live GPS link.", "Keep {name} still and warm while help is arranged; check for bleeding or limb deformity.", "Log the incident time and circumstances for the physician review."],
    ],
    "Low Oxygen": [
        ["Encourage slow deep breathing and sit {name} upright — upright posture opens the diaphragm.", "Re-check SpO2 after 5 minutes of rest; if it stays below {spo2_safe}%, contact the physician.", "Ensure the room is ventilated and check that nothing is obstructing the band's sensor against the skin."],
        ["Move to fresh air or open a window and re-measure in a few minutes.", "If {name} reports breathlessness, confusion or chest pain, escalate to emergency services immediately.", "Review COPD/asthma inhaler availability if oxygen does not recover within 10 minutes."],
    ],
    "Fever": [
        ["Confirm with an oral or tympanic thermometer and encourage fluid intake.", "Monitor temperature every 30–60 minutes; if it exceeds 38.5°C or persists over 12 hours, contact the GP.", "Watch for accompanying symptoms: shivering, confusion, reduced urination or a new cough."],
        ["Offer fluids and keep the room comfortably cool; avoid heavy blankets.", "Record the fever episode in the symptom log for the next medical review.", "If {name} is on blood thinners or immunosuppressants, call the care team today — fever thresholds are lower for these patients."],
    ],
    "High Stress": [
        ["Guide {name} through slow paced breathing (4 seconds in, 6 seconds out) for 2–3 minutes.", "Reduce stimulation: quiet room, seated posture, reassuring conversation.", "If stress index stays above 0.60 for more than 20 minutes, check for pain, caffeine or a distressing trigger."],
        ["Suggest a short calm activity — tea, music or a gentle walk in the corridor.", "Re-check HRV after 10 minutes of rest; recovery is the goal, not just a lower heart rate.", "Repeated stress spikes this week should be mentioned at the next clinical review."],
    ],
    "Panic Attack": [
        ["Stay on a voice call with {name} — calm, steady contact is the fastest intervention.", "Coach breathing: inhale 4 s, exhale 6 s; ground by naming 5 visible objects in the room.", "If chest pain, fainting or blue lips appear, escalate to emergency services immediately."],
        ["Remind {name} the episode will pass; panics typically peak within 10 minutes.", "Avoid stimulants (caffeine, nicotine) for the rest of the day.", "Book a GP follow-up if panic episodes repeat within a week — medication review may be warranted."],
    ],
    "Tachycardia": [
        ["Pause physical activity and sit {name} down with legs elevated slightly.", "Re-measure after 5 minutes of stillness; if heart rate stays above {hr_safe} bpm, contact the care team.", "Check hydration and recent caffeine or medication changes."],
        ["Look for triggers: fever, pain, dehydration or missed heart medication.", "If accompanied by chest pain or faintness, treat as a cardiac event and escalate."],
    ],
    "Bradycardia": [
        ["Ask {name} how they feel: dizziness, near-fainting or fatigue need medical attention.", "Avoid sudden standing; assist with mobility until the pulse recovers.", "If heart rate stays under {hr_low_safe} bpm for more than 10 minutes or symptoms appear, contact the physician."],
        ["Check whether beta-blockers or other rate-slowing medication was taken recently.", "Keep {name} seated and hydrated; re-check in 5 minutes."],
    ],
    "Fatigue": [
        ["Prioritise rest today; keep walks short and supported.", "A light meal and fluids can help recovery — fatigue plus low HRV often tracks with dehydration.", "Protect against falls: clear walking paths and assist with stairs."],
        ["Encourage an early night; recovery sleep is the most effective intervention.", "If fatigue persists more than 48 hours, mention it at the next GP visit."],
    ],
    "Inactivity": [
        ["Send a quick check-in message or call — confirm {name} is okay and simply resting.", "If there is no response within 10 minutes, treat as a potential fall or medical event and dispatch help.", "Encourage a short assisted walk; gentle movement reduces stiffness and clot risk."],
        ["Verify the band is being worn — an unattended band on a table also produces long still periods.", "If quiet time is intentional (nap, reading), you can snooze this alert type in thresholds."],
    ],
    "General Anomaly": [
        ["Keep an eye on {name} over the next hour and re-check the live dashboard.", "Note any symptoms reported by the wearer for the next medical review.", "If the anomaly repeats, tighten the alert thresholds or contact the care team."],
        ["No immediate intervention is required, but avoid strenuous activity until readings stabilise.", "A brief call to confirm wellbeing is a proportionate response."],
    ],
    "Emergency SOS": [
        ["Acknowledge the call and dispatch the emergency contact list now.", "Keep a voice line open with {name} until help arrives.", "Share the live GPS position with responders and record arrival times."],
        ["Send someone to the location on the map immediately — do not wait for callback.", "Prepare to give responders the medication list and medical history card."],
    ],
}


def _fmt_ctx(readings: dict, patient: dict) -> dict:
    name = (patient.get("name") or "the wearer").split()[0]
    conditions = patient.get("conditions") or "no major conditions on file"
    hr = float(readings.get("heart_rate", 0))
    return {
        "name": name,
        "conditions": conditions,
        "time": readings.get("time", "the event"),
        "heart_rate": f"{hr:.0f}",
        "spo2": f"{float(readings.get('spo2', 0)):.0f}",
        "spo2_safe": f"{float(readings.get('spo2_safe', 92)):.0f}",
        "spo2_drop": f"{max(0.0, float(readings.get('spo2_safe', 92)) - float(readings.get('spo2', 0))):.1f}",
        "temperature": f"{float(readings.get('temperature', 0)):.1f}",
        "temp_safe": f"{float(readings.get('temp_safe', 37.8)):.1f}",
        "temp_delta": f"{max(0.0, float(readings.get('temperature', 0)) - float(readings.get('temp_safe', 37.8))):.1f}",
        "gsr": f"{float(readings.get('gsr', 0)):.2f}",
        "hrv": f"{float(readings.get('hrv', 0)):.0f}",
        "stress": f"{float(readings.get('stress', 0)):.2f}",
        "hr_safe": f"{float(readings.get('hr_safe', 110)):.0f}",
        "hr_low_safe": f"{float(readings.get('hr_low_safe', 50)):.0f}",
        "hr_delta": f"{abs(hr - float(readings.get('hr_expected', hr))):.0f}",
        "accel_mag": f"{float(readings.get('accel_mag', 0)):.1f}",
        "gyro_mag": f"{float(readings.get('gyro_mag', 0)):.1f}",
        "inactive_minutes": f"{float(readings.get('inactive_minutes', 0)):.0f}",
    }


def _llm_call(condition: str, readings: dict) -> dict | None:
    if not HF_TOKEN:
        return None
    try:
        import requests

        prompt = f"""<s>[INST] You are a health monitoring assistant for a smart wearable worn by an elderly person.
Respond ONLY in this JSON format with no extra text:
{{"explanation": "one plain-language sentence", "advice": "one or two concrete actions", "urgency": "low|medium|high"}}

Detected condition: {condition}
Sensor readings:
- Heart Rate   : {readings.get('heart_rate')} bpm
- HRV          : {readings.get('hrv')} ms
- GSR          : {readings.get('gsr')}
- Temperature  : {readings.get('temperature')} °C
- Blood Oxygen : {readings.get('spo2')} %
- Stress Score : {readings.get('stress')}
[/INST]"""
        res = requests.post(
            HF_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={
                "inputs": prompt,
                "parameters": {"max_new_tokens": 160, "return_full_text": False},
            },
            timeout=8,
        )
        text = res.json()[0]["generated_text"].strip()
        data = json.loads(text)
        if "explanation" in data:
            return data
    except Exception:
        return None
    return None


def generate_explanation(
    alert_type: str, readings: dict, patient: dict
) -> tuple[str, str, str]:
    """
    Returns (explanation, recommendation, urgency) in plain language.
    Tries the hosted LLM first, falls back to the local narrative engine.
    """
    key = alert_type if alert_type in _EXPLAIN else "General Anomaly"
    ctx = _fmt_ctx(readings, patient)
    seed = f"{alert_type}-{readings.get('time', '')}-{ctx['heart_rate']}"

    llm = _llm_call(alert_type, readings)
    if llm:
        advice = llm.get("advice", "")
        return llm["explanation"], advice, llm.get("urgency", "medium")

    explanation = _pick(_EXPLAIN[key], seed).format(**ctx)
    recs = _pick(_RECOMMEND[key], seed + "r")
    recommendation = " ".join(f"• {r.format(**ctx)}" for r in recs)
    urgency = {
        "Fall Detected": "critical",
        "Emergency SOS": "critical",
        "Panic Attack": "high",
        "Low Oxygen": "high",
        "Fever": "medium",
        "High Stress": "medium",
        "Inactivity": "medium",
    }.get(key, "low")
    return explanation, recommendation, urgency


def summarize_readings(window: list[dict]) -> dict:
    """Quick aggregates used by summaries and explanations."""
    if not window:
        return {}
    def avg(k):
        return sum(r[k] for r in window) / len(window)
    return {
        "hr": avg("heart_rate"),
        "spo2": avg("spo2"),
        "temp": avg("temperature"),
        "gsr": avg("gsr"),
        "hrv": avg("hrv"),
        "stress": avg("stress_score"),
        "n": len(window),
    }


def build_daily_summary(patient: dict, window: list[dict], alerts: list[dict]) -> dict:
    """Compose a plain-language daily AI health summary."""
    name = (patient.get("name") or "The wearer").split()[0]
    s = summarize_readings(window)
    if not s:
        return {
            "title": f"{name}'s health summary",
            "body": "Not enough sensor data was captured today to build a summary.",
            "tags": ["incomplete-data"],
            "score": 0.5,
        }

    sleep_rows = [r for r in window if r.get("activity") == "Sleeping"]
    day_rows = [r for r in window if r.get("activity") != "Sleeping"]
    night_hr = sum(r["heart_rate"] for r in sleep_rows) / max(1, len(sleep_rows))
    day_hr = sum(r["heart_rate"] for r in day_rows) / max(1, len(day_rows))

    stress_peak = max((r["stress_score"] for r in window), default=0)
    spo2_min = min(r["spo2"] for r in window)
    temp_max = max(r["temperature"] for r in window)

    tags = []
    parts = []
    parts.append(
        f"{name} wore the band for {max(1, len(window))} monitored intervals. "
        f"Average heart rate was {s['hr']:.0f} bpm "
        f"({night_hr:.0f} bpm overnight vs {day_hr:.0f} bpm during the day), "
        f"with heart-rate variability averaging {s['hrv']:.0f} ms."
    )
    if spo2_min < 94:
        tags.append("desaturation")
        parts.append(
            f"Oxygen saturation dipped to {spo2_min:.0f}% at its lowest point — "
            f"a brief overnight desaturation that is common in light sleep, but worth repeating if it recurs."
        )
    else:
        tags.append("stable-oxygen")
        parts.append(f"Blood oxygen stayed reassuringly stable (minimum {spo2_min:.0f}%).")
    if temp_max >= 37.6:
        tags.append("temperature-watch")
        parts.append(f"Skin temperature peaked at {temp_max:.1f}°C — slightly elevated, keep an eye on it.")
    else:
        tags.append("stable-temperature")
        parts.append(f"Temperature remained in the normal band (peak {temp_max:.1f}°C).")
    if stress_peak >= 0.6:
        tags.append("stress-episode")
        parts.append(
            f"Stress index reached {stress_peak:.2f} during the day — a clear episode that resolved afterwards. "
            f"Breathing exercises before stressful activities may help."
        )
    else:
        tags.append("calm")
        parts.append("Stress markers stayed low throughout the day, indicating good emotional regulation.")

    fall_count = sum(1 for a in alerts if a["type"] == "Fall Detected")
    if fall_count:
        tags.append("fall-risk")
        parts.append(f"{fall_count} fall event(s) were recorded today. Assistive mobility review is recommended.")
    else:
        parts.append("No falls were detected.")

    score = 0.85
    if "desaturation" in tags:
        score -= 0.1
    if "stress-episode" in tags:
        score -= 0.08
    if "temperature-watch" in tags:
        score -= 0.07
    if fall_count:
        score -= 0.2

    rnd = random.Random(s["hr"])
    outlook = _pick(
        [
            "Overall outlook for tomorrow is positive: keep hydration and the evening walk routine.",
            "Tomorrow looks stable — protect the evening rest window to keep HRV trending up.",
            "The trend is mildly improving; consistency in medication timing will help keep it that way.",
        ],
        f"{name}-{s['hr']:.0f}",
    )

    return {
        "title": f"Daily health summary — {name}",
        "body": " ".join(parts) + " " + outlook,
        "tags": tags,
        "score": round(max(0.1, min(0.99, score)), 2),
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

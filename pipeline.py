import json
import requests
import joblib
import numpy as np
import pandas as pd
from collections import deque
from tensorflow.keras.models import load_model

# ── Load models (once at startup) ────────────────────────────────────────────
activity_clf = joblib.load('models/activity_classifier.pkl')
iso_forest   = joblib.load('models/isolation_forest.pkl')
scaler       = joblib.load('models/scaler.pkl')
autoencoder  = load_model('models/lstm_autoencoder.keras')

with open('models/pipeline_stats.json') as f:
    STATS = json.load(f)

# ── Constants ─────────────────────────────────────────────────────────────────
ACTIVITY_FEATURES = [
    'Accel_X', 'Accel_Y', 'Accel_Z',
    'Gyro_X',  'Gyro_Y',  'Gyro_Z',
    'Step_Count'
]
NUMERIC_FEATURES = [
    'Heart_Rate', 'Body_Temperature', 'Blood_Oxygen', 'Step_Count',
    'Accel_X', 'Accel_Y', 'Accel_Z',
    'Gyro_X',  'Gyro_Y',  'Gyro_Z',
    'GSR_Value', 'HRV', 'Sweat_Response',
    'Activity_Intensity',
    'Accel_Magnitude', 'Gyro_Magnitude',
    'HR_HRV_Ratio', 'Stress_Score',
    'SpO2_Risk', 'Fever_Risk', 'HR_Deviation',
    'HR_per_Activity', 'HRV_Adjusted'
]
ACTIVITY_INTENSITY_MAP = {
    'Sleeping': 1, 'Resting': 2, 'Walking': 3,
    'Running':  4, 'Exercising': 5
}
EXPECTED_HR = {1: 60, 2: 75, 3: 100, 4: 160, 5: 150}
TIMESTEPS   = 10

# ── Sliding window buffer (keeps last N scaled readings for LSTM) ─────────────
reading_buffer: deque = deque(maxlen=TIMESTEPS)

# ── LLM config (optional — set your HF token to enable) ──────────────────────
HF_TOKEN = ""    # paste your HuggingFace token here
HF_URL   = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

# ── Step 1: Feature Engineering ───────────────────────────────────────────────
def build_features(raw: dict) -> dict:
    r = raw.copy()

    # Activity classifier → intensity
    act_input     = np.array([[r[f] for f in ACTIVITY_FEATURES]])
    activity_pred = activity_clf.predict(act_input)[0]
    intensity     = ACTIVITY_INTENSITY_MAP.get(activity_pred, 2)

    r['Activity_Predicted'] = activity_pred
    r['Activity_Intensity'] = intensity

    # Motion magnitudes
    r['Accel_Magnitude'] = float(np.sqrt(r['Accel_X']**2 + r['Accel_Y']**2 + r['Accel_Z']**2))
    r['Gyro_Magnitude']  = float(np.sqrt(r['Gyro_X']**2  + r['Gyro_Y']**2  + r['Gyro_Z']**2))

    # Health features
    r['HR_HRV_Ratio']    = r['Heart_Rate'] / (r['HRV'] + 1e-6)
    r['SpO2_Risk']       = max(0.0, 98.0 - r['Blood_Oxygen'])
    r['Fever_Risk']      = max(0.0, r['Body_Temperature'] - 37.2)
    r['HR_Deviation']    = r['Heart_Rate'] - EXPECTED_HR.get(intensity, 75)
    r['HR_per_Activity'] = r['Heart_Rate'] / intensity
    r['HRV_Adjusted']    = r['HRV'] * intensity

    # Stress score — uses training min/max saved in pipeline_stats.json
    gsr_min, gsr_max = STATS['gsr_min'], STATS['gsr_max']
    hrv_min, hrv_max = STATS['hrv_min'], STATS['hrv_max']
    r['Stress_Score'] = (
        (r['GSR_Value'] - gsr_min) / (gsr_max - gsr_min + 1e-6)
        + 1 - (r['HRV'] - hrv_min) / (hrv_max - hrv_min + 1e-6)
    ) / 2

    return r

# ── Step 2: Isolation Forest ──────────────────────────────────────────────────
def run_isolation_forest(features: dict) -> tuple[int, float]:
    row    = pd.DataFrame([[features[f] for f in NUMERIC_FEATURES]], columns=NUMERIC_FEATURES)
    scaled = scaler.transform(row)
    score  = float(iso_forest.decision_function(scaled)[0])
    label  = -1 if score < STATS['if_threshold'] else 1
    return label, score

# ── Step 3: LSTM Autoencoder ──────────────────────────────────────────────────
def run_lstm(scaled_row: np.ndarray) -> tuple[int, float]:
    """
    Needs TIMESTEPS readings in buffer before it can predict.
    Returns (1, 0.0) = normal while buffer is filling up.
    """
    reading_buffer.append(scaled_row)

    if len(reading_buffer) < TIMESTEPS:
        return 1, 0.0

    seq   = np.array(list(reading_buffer))[np.newaxis, ...]  # (1, TIMESTEPS, N_FEATURES)
    recon = autoencoder.predict(seq, verbose=0)
    mae   = float(np.mean(np.abs(recon - seq)))
    label = -1 if mae > STATS['lstm_threshold'] else 1
    return label, mae

# ── Step 4: Condition classifier ──────────────────────────────────────────────
def classify_condition(features: dict, if_label: int) -> str:
    if if_label != -1:
        return 'Normal'
    if features['Fever_Risk'] >= 0.8:
        return 'Fever'
    if features['SpO2_Risk'] >= 3.0:
        return 'Low Oxygen'
    if features['Accel_Magnitude'] >= 2.8 and features['Gyro_Magnitude'] >= 2.8:
        return 'Fall Detected'
    if features['HR_Deviation'] >= 35 and features['Stress_Score'] >= 0.70:
        return 'Panic Attack'
    if features['Stress_Score'] >= 0.60 and features['HR_HRV_Ratio'] >= 1.6:
        return 'Stress'
    if features['HRV'] <= 25:
        return 'Fatigue'
    return 'General Anomaly'

# ── Step 5 (optional): LLM advice ────────────────────────────────────────────
def call_llm(condition: str, features: dict) -> dict | None:
    if not HF_TOKEN or condition == 'Normal':
        return None

    prompt = f"""<s>[INST] You are a health monitoring assistant for a smart wearable. \
Respond ONLY in this JSON format with no extra text:
{{"explanation": "one sentence", "advice": "one or two actions", "urgency": "low|medium|high"}}

Detected condition: {condition}
Sensor readings:
- Heart Rate   : {features['Heart_Rate']:.0f} bpm
- HRV          : {features['HRV']:.1f} ms
- GSR          : {features['GSR_Value']:.2f}
- Temperature  : {features['Body_Temperature']:.1f} °C
- Blood Oxygen : {features['Blood_Oxygen']:.1f} %
- Stress Score : {features['Stress_Score']:.2f}
- HR Deviation : {features['HR_Deviation']:.0f} bpm above expected for activity
[/INST]"""

    try:
        res = requests.post(
            HF_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": 150, "return_full_text": False}},
            timeout=10
        )
        text = res.json()[0]['generated_text'].strip()
        return json.loads(text)
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return None

# ── Main entry point ──────────────────────────────────────────────────────────
def process_reading(raw: dict) -> dict:
    # Feature engineering
    features = build_features(raw)

    # Scale once — reused by both IF and LSTM
    row_df = pd.DataFrame([[features[f] for f in NUMERIC_FEATURES]], columns=NUMERIC_FEATURES)
    scaled = scaler.transform(row_df)[0]

    # Detectors
    if_label,   if_score  = run_isolation_forest(features)
    lstm_label, lstm_mae  = run_lstm(scaled)

    # Condition
    condition = classify_condition(features, if_label)

    # Ensemble
    if if_label == -1 and lstm_label == -1:
        ensemble = 'High Confidence Anomaly'
    elif if_label == -1 or lstm_label == -1:
        ensemble = 'Low Confidence Anomaly'
    else:
        ensemble = 'Normal'

    # LLM (only fires on anomalies, only if token is set)
    llm_advice = call_llm(condition, features)

    return {
        'vitals': {
            'heart_rate':   round(raw['Heart_Rate'], 1),
            'temperature':  round(raw['Body_Temperature'], 1),
            'blood_oxygen': round(raw['Blood_Oxygen'], 1),
            'hrv':          round(raw['HRV'], 1),
            'gsr':          round(raw['GSR_Value'], 2),
            'activity':     features['Activity_Predicted'],
        },
        'scores': {
            'if_score':    round(if_score, 4),
            'lstm_mae':    round(lstm_mae, 4),
            'stress':      round(features['Stress_Score'], 3),
        },
        'condition':  condition,
        'ensemble':   ensemble,
        'llm_advice': llm_advice,
    }

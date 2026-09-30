"""Deck section C — intelligence: equation engine, calibration, detection catalogue, safety model, AI layer."""
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE

from kit import *


def build(b):
    intelligence(b)
    calibration(b)
    detection(b)
    safety(b)
    ailayer(b)


# ─────────────────────────── 11 intelligence ───────────────────────────
def intelligence(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "03 / Intelligence", "Explainable AI without a training dataset",
           "Population ML needs data the wearer never generated. Physiological equations plus per-wearer "
           "calibration work on day one — and every number can be defended.", num=n)

    # ── equation table
    rows = [["Equation", "Form", "What it answers"],
            ["Robust z-score", "z = (x − median) / (1.4826 · MAD)", "How far is this reading from HER normal, resistant to outliers?"],
            ["EDA split", "tonic = EWMA(GSR) · phasic = max(0, GSR − tonic)", "Is this slow arousal or a sudden sympathetic spike?"],
            ["Stress index", "S = clamp(0.5 + Σσ-evidence / 5)", "Combined stress evidence from GSR, HRV and heart rate at rest"],
            ["Core temperature", "T_core ≈ gain · T_skin + offset", "Skin reading converted to a core-equivalent, personally offset"],
            ["Fever score", "core level + °C/h slope + HR↔T coupling", "Is this a real fever trend or a warm room?"],
            ["Hypoxic burden", "B ← 0.85 · B + minutes · max(0, 92 − SpO₂)", "Sustained desaturation instead of a single noisy sample"],
            ["Fall physics", "free-fall → impact ≥ 2.8 g → tumble ≥ 2.4 rad/s → stillness", "Four-stage signature that separates a fall from a bump"],
            ["Expected HR", "HR_exp = HR_rest + activity demand · age factor", "Is this pulse appropriate for what she is doing right now?"]]
    table(s, ML, 1.74, [1.90, 4.24, 5.63], rows, row_h=0.40, head_h=0.32,
          size=8.5, head_size=8, bold_col0=True, align=["l", "l", "l"])

    # ── right-of-bottom notes
    card(s, ML, 5.32, 5.60, 1.58, fill=SURF2)
    tx(s, ML + 0.24, 5.50, 5.1, 0.24, "WHY IT MATTERS COMMERCIALLY", size=8, color=MUTED, bold=True, track=110)
    bullets(s, ML + 0.24, 5.78, 5.1, 1.0,
            ["A new wearer is covered on day one — no cold-start gap.",
             "Every alert can be explained in a sentence to a clinician or a regulator.",
             "The same formulas run on the wrist, so cost does not scale with users."],
            size=8.5, dot="·", gap=3, line=1.22)

    card(s, ML + 5.86, 5.32, 5.91, 1.58, fill=SURF)
    tx(s, ML + 6.10, 5.50, 5.4, 0.24, "LEGACY ML ASSETS (KEPT, SUPERSEDED)", size=8, color=MUTED, bold=True, track=110)
    tx(s, ML + 6.10, 5.78, 5.4, 0.36,
       "An offline pipeline with Isolation Forest, an LSTM autoencoder and an activity classifier remains "
       "in the repository for research comparison.", size=8.5, color=TEXT2, line=1.25)
    rich(s, ML + 6.10, 6.24, 5.4, 0.5, [{"runs": [
        {"t": "1,875 ", "size": 10, "bold": True, "color": INK}, {"t": "training rows · ", "size": 8, "color": MUTED},
        {"t": "14 ", "size": 10, "bold": True, "color": INK}, {"t": "channels · ", "size": 8, "color": MUTED},
        {"t": "IF threshold −0.02 · LSTM AE 0.332.  ", "size": 8, "color": MUTED},
        {"t": "Not used for live detection.", "size": 8, "bold": True, "color": ACCENT}]}])
    footer(s, n, right="Intelligence")


# ─────────────────────────── 12 calibration ────────────────────────────
def calibration(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "03 / Intelligence", "The model learns one body, not a population",
           "Four sources of truth, tracked per baseline, with confidence that grows as the band is worn.", num=n)

    # four source cards
    srcs = [("AUTO", "Every stream tick", "Slow EWMA baselines with a quiet gate, so a crisis reading never drags "
             "the baseline; robust MAD tracks personal noise.", ACCENT),
            ("AUTO-FIT", "Last 24 h of data", "Snapshots baselines to robust percentiles of stored vitals and shows "
             "a before / after diff before committing.", ACCENT3),
            ("GUIDED", "Reference instrument", "Oral thermometer, clinical pulse oximeter, measured resting HR/HRV — "
             "each logged with a timestamp.", PURPLE),
            ("MANUAL", "Clinician or caregiver", "Direct overrides when a professional knows the wearer better than "
             "the data yet does.", OK)]
    for i, (tag, when, body, col) in enumerate(srcs):
        x = gx(i * 3)
        card(s, x, 1.74, gw(3, 0.22), 2.06, fill=SURF)
        tx(s, x + 0.22, 1.92, 2.6, 0.22, tag, size=8.5, color=col, bold=True, track=130)
        tx(s, x + 0.22, 2.16, gw(3, 0.6), 0.22, when, size=9, color=MUTED)
        hline(s, x + 0.22, 2.48, gw(3, 0.44), color=BORDER, lw=0.75)
        tx(s, x + 0.22, 2.62, gw(3, 0.44), 1.0, body, size=9, color=TEXT2, line=1.3)

    # guided-reference worked example
    card(s, ML, 3.96, 5.60, 2.94, fill=SURF2)
    tx(s, ML + 0.26, 4.14, 5.1, 0.24, "WORKED EXAMPLE — GUIDED CORE-TEMPERATURE OFFSET", size=8, color=MUTED, bold=True, track=100)
    steps = [("1", "Nurse takes an oral temperature", "37.1 °C"),
             ("2", "Band reports skin temperature at that moment", "36.5 °C"),
             ("3", "Personal skin → core offset is stored", "+0.6 °C"),
             ("4", "Every later reading uses the personal offset", "core-equiv. T")]
    sy = 4.46
    for i, (idx, t, v) in enumerate(steps):
        oval(s, ML + 0.26, sy + 0.02, 0.26, 0.26, LAV_SOFT)
        tx(s, ML + 0.26, sy + 0.05, 0.26, 0.2, idx, size=7.5, color=ACCENT, bold=True, align="c")
        tx(s, ML + 0.64, sy, 3.5, 0.24, t, size=9, color=TEXT2, anchor="m")
        tx(s, ML + 4.16, sy, 1.2, 0.24, v, size=9.5, color=INK, bold=True, align="r", anchor="m")
        if i < 3:
            hline(s, ML + 0.26, sy + 0.36, 5.1, color=BORDER, lw=0.5)
        sy += 0.54
    tx(s, ML + 0.26, 6.52, 5.1, 0.3,
       "Fever now triggers on a core-equivalent temperature, not on a warm forearm.",
       size=8.5, color=ACCENT, line=1.25)

    # baseline table + status
    x = 6.72
    tx(s, x, 3.96, 5.05, 0.24, "BASELINES TRACKED PER WEARER", size=8, color=MUTED, bold=True, track=110)
    rows = [["Baseline", "Example value", "Source"],
            ["Resting heart rate", "68 bpm", "auto"],
            ["Resting HRV (RMSSD)", "44 ms", "guided"],
            ["Tonic skin conductance", "0.42 µS", "auto"],
            ["Skin temperature", "36.4 °C", "auto"],
            ["SpO₂ offset", "−0.5 %", "guided"],
            ["Skin → core offset", "+0.6 °C", "guided"]]
    table(s, x, 4.22, [2.30, 1.55, 1.20], rows, row_h=0.25, head_h=0.26, size=8.5, head_size=7.5,
          bold_col0=True, align=["l", "r", "c"], head_align=["l", "r", "c"])

    card(s, x, 6.04, 5.05, 0.86, fill=SURF)
    tx(s, x + 0.20, 6.14, 4.6, 0.22, "STATUS FLOW", size=7.5, color=MUTED, bold=True, track=110)
    for i, (t, col, bgc) in enumerate([("warming_up", WARN, WARN_BG), ("→", MUTED, None), ("active", OK, OK_BG),
                                       ("with confidence %", MUTED, None)]):
        if bgc:
            chip(s, x + 0.20 + i * 1.24, 6.44, 1.12, 0.30, t, fg=col, bgc=bgc, size=8, track=20)
        else:
            tx(s, x + 0.20 + i * 1.24, 6.44, 1.16, 0.30, t, size=8, color=col, anchor="m")
    footer(s, n, right="Intelligence")


# ─────────────────────────── 13 detection ──────────────────────────────
def detection(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "03 / Intelligence", "Eight conditions, each with its own evidence",
           "Alerts carry severity, the readings that fired, a plain-language explanation and suggested next steps.",
           num=n)

    rows = [["Condition", "Severity range", "Signals that fire it", "Tier"],
            ["Fall Detected", "critical", "accel ≥ 2.8 g with tumble ≥ 2.4 rad/s plus post-impact stillness", "Clinical floor"],
            ["Low Oxygen", "high → critical", "SpO₂ < 92 % / < 90 %, or accumulated hypoxic burden ≥ 3 %·min", "Both tiers"],
            ["Fever", "medium → high", "skin ≥ 37.8 °C or core-equivalent ≥ 37.8 °C, plus °C/h slope and HR coupling", "Both tiers"],
            ["Panic Attack", "critical", "stress index ≥ 0.72 with HR ≥ 30 bpm above activity expectation", "Both tiers"],
            ["High Stress", "medium → high", "stress index ≥ 0.60 or personal z ≥ 2.0σ on combined stress evidence", "Both tiers"],
            ["Tachycardia", "medium → high", "resting HR ≥ 110 bpm, severe from ≥ 135 bpm (absolute floor 140)", "Clinical floor"],
            ["Bradycardia", "medium → high", "HR ≤ 50 bpm at rest (absolute floor 38 bpm)", "Clinical floor"],
            ["Fatigue", "low", "HRV ≤ 20 ms or a ≥ 40 % drop versus the personal resting HRV", "Both tiers"],
            ["Inactivity", "medium → high", "no movement for the configured window, with a 24 h safety watch", "Personal rule"]]
    table(s, ML, 1.74, [1.72, 1.34, 6.51, 1.40], rows, row_h=0.34, head_h=0.30,
          size=8.5, head_size=7.5, bold_col0=True, align=["l", "l", "l", "l"])

    # alert anatomy strip
    card(s, ML, 5.24, 7.40, 1.66, fill=SURF)
    tx(s, ML + 0.24, 5.40, 6.9, 0.24, "ANATOMY OF ONE ALERT — WHAT A CAREGIVER ACTUALLY RECEIVES",
       size=8, color=MUTED, bold=True, track=100)
    chip(s, ML + 0.24, 5.70, 0.80, 0.26, "CRITICAL", fg=DANGER, bgc=DANGER_BG, size=7.5)
    tx(s, ML + 1.14, 5.70, 3.4, 0.26, "Fall detected — impact signature", size=10.5, color=INK, bold=True, anchor="m")
    tx(s, ML + 4.60, 5.68, 2.8, 0.28, "02:15 · bathroom · GPS captured", size=8, color=MUTED, align="r", anchor="m")
    tx(s, ML + 0.24, 6.06, 6.9, 0.72,
       "“Acceleration spiked to 3.4 g with 2.9 rad/s of rotation, followed by 40 s without movement. "
       "Heart rate rose to 112 bpm afterwards. This matches a fall signature rather than a stumble.”  "
       "→  Recommended: call the wearer, then dispatch the primary contact.",
       size=8.5, color=TEXT2, line=1.32)

    card(s, ML + 7.66, 5.24, 4.11, 1.66, fill=SURF2)
    tx(s, ML + 7.90, 5.40, 3.7, 0.24, "COVERAGE OF THE LIVE SUITE", size=8, color=MUTED, bold=True, track=100)
    for i, (v, l) in enumerate([("8", "conditions + inactivity watch"), ("2", "independent trigger tiers"),
                                ("11", "immutable clinical safety floors")]):
        rich(s, ML + 7.90, 5.74 + i * 0.36, 3.74, 0.40, [{"runs": [
            {"t": v + "  ", "size": 12, "bold": True, "color": ACCENT},
            {"t": l, "size": 7.5, "color": TEXT2}]}])
    footer(s, n, right="Detection")


# ─────────────────────────── 14 safety model ───────────────────────────
def safety(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "03 / Intelligence", "Personalisation may add sensitivity, never remove it",
           "Every condition is evaluated twice — against fixed clinical floors and against the wearer's own baselines.",
           num=n)

    # two tier columns
    card(s, ML, 1.82, 5.72, 3.34, fill=SURF)
    rect(s, ML, 1.82, 5.72, 0.05, fill=DANGER, radius=True, adj=0.5)
    tx(s, ML + 0.26, 2.02, 5.2, 0.24, "TIER 1 — CLINICAL FLOORS (READ-ONLY)", size=8.5, color=DANGER, bold=True, track=110)
    tx(s, ML + 0.26, 2.30, 5.2, 0.46,
       "Guideline constants that calibration can never move. A personal baseline must never make a "
       "clinical emergency look safe.", size=9, color=TEXT2, line=1.28)
    floors = [("SpO₂ urgent / low", "90 % / 92 %"), ("Core-equivalent fever", "≥ 37.8 °C"),
              ("Hypothermia", "≤ 35.5 °C"), ("Urgent tachycardia", "≥ 140 bpm"),
              ("Urgent bradycardia", "≤ 38 bpm"), ("Fall impact", "≥ 2.8 g"),
              ("Tumble rotation", "≥ 2.4 rad/s")]
    fy = 2.94
    for i, (k, v) in enumerate(floors):
        rich(s, ML + 0.26 + (i % 2) * 2.66, fy + (i // 2) * 0.42, 2.6, 0.32, [{"runs": [
            {"t": k + "  ", "size": 8.5, "color": MUTED}, {"t": v, "size": 9, "bold": True, "color": INK}]}])
    tx(s, ML + 0.26, 4.62, 5.2, 0.4,
       "Immutable in the product: no caregiver edit, no calibration result and no model update can raise or lower these.",
       size=8, color=DANGER, line=1.25)

    card(s, ML + 6.05, 1.82, 5.72, 3.34, fill=SURF)
    rect(s, ML + 6.05, 1.82, 5.72, 0.05, fill=OK, radius=True, adj=0.5)
    tx(s, ML + 6.31, 2.02, 5.2, 0.24, "TIER 2 — PERSONAL σ-RULES (EDITABLE)", size=8.5, color=OK, bold=True, track=110)
    tx(s, ML + 6.31, 2.30, 5.2, 0.46,
       "Deviations versus the wearer's own baselines — the tier that catches what a population threshold "
       "would miss.", size=9, color=TEXT2, line=1.28)
    rules = [("Stress evidence", "z ≥ 2.0σ"), ("Fever deviation", "z ≥ 2.5σ"),
             ("Heart-rate deviation", "z ≥ 2.5σ"), ("HRV drop vs personal rest", "≥ 40 %"),
             ("Hypoxic burden", "≥ 3 %·min"), ("Inactivity window", "configurable")]
    for i, (k, v) in enumerate(rules):
        rich(s, ML + 6.31 + (i % 2) * 2.70, 2.94 + (i // 2) * 0.42, 2.6, 0.32, [{"runs": [
            {"t": k + "  ", "size": 8.5, "color": MUTED}, {"t": v, "size": 9, "bold": True, "color": INK}]}])
    tx(s, ML + 6.31, 4.24, 5.2, 0.28, "Live in Management → Calibration. Adjustable without a redeploy.",
       size=8, color=OK, line=1.25)
    hbar(s, ML + 6.31, 4.66, 3.2, 0.10, 0.40, color=OK)
    tx(s, ML + 6.31, 4.80, 5.2, 0.28, "Sensitivity slider shown to the caregiver: less sensitive  ←→  more sensitive",
       size=7.5, color=MUTED)

    # OR-gate band
    card(s, ML, 5.34, CW, 1.56, fill=ACCENT, line=None)
    tx(s, ML + 0.30, 5.52, 4.0, 0.24, "THE TRIGGER RULE", size=8, color=LAV, bold=True, track=120)
    tx(s, ML + 0.30, 5.80, 3.5, 0.7,
       "A condition fires when\nEITHER tier fires.", size=15, color=LIGHT, bold=True, line=1.18)
    gates = [("Tier 1 fires", "→ alert", DANGER_BG, DANGER),
             ("Tier 2 fires", "→ alert", OK_BG, OK),
             ("Both fire", "→ higher severity", LAV_SOFT, ACCENT)]
    for i, (t, sub, bgc, col) in enumerate(gates):
        bx = ML + 4.20 + i * 2.58
        rect(s, bx, 5.74, 2.38, 0.80, fill=bgc, radius=True, adj=0.18)
        tx(s, bx + 0.18, 5.88, 2.0, 0.24, t, size=10, color=col, bold=True)
        tx(s, bx + 0.18, 6.12, 2.0, 0.22, sub, size=9, color=col)
    tx(s, ML + 0.30, 6.56, 11.6, 0.24,
       "Personalisation is therefore an asymmetry in safety, not a trade-off: it can only ever add sensitivity.",
       size=8.5, color=LIGHT2)
    footer(s, n, right="Safety model")


# ─────────────────────────────── 15 AI layer ───────────────────────────
def ailayer(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "03 / Intelligence", "Three layers of explanation, one language layer",
           "Rules decide. Equations quantify. A language layer translates — and degrades gracefully.",
           num=n)

    layers = [("01", "Detection rules", "Deterministic", "Threshold and σ-gates decide whether an event exists at all. "
               "No probabilistic model sits between the sensor and the decision.", ACCENT),
              ("02", "Equation evidence", "Quantified", "The alert stores its own evidence: z-scores, core-equivalent "
               "temperature, hypoxic burden, HR vs activity expectation.", ACCENT3),
              ("03", "Language layer", "Narrated", "A hosted model turns that evidence into a caregiver-readable "
               "explanation and next steps — with a deterministic template fallback offline.", PURPLE)]
    for i, (idx, t, tag, body, col) in enumerate(layers):
        y = 1.80 + i * 1.18
        card(s, ML, y, 7.40, 1.02, fill=SURF)
        tx(s, ML + 0.24, y + 0.16, 0.6, 0.24, idx, size=9, color=col, bold=True, track=90)
        tx(s, ML + 0.86, y + 0.14, 2.6, 0.26, t, size=11.5, color=INK, bold=True)
        chip(s, ML + 3.52, y + 0.14, 1.10, 0.24, tag.upper(), fg=col, bgc=SURF2, size=7, track=40)
        tx(s, ML + 0.86, y + 0.46, 6.2, 0.48, body, size=9, color=TEXT2, line=1.28)
        if i < 2:
            tx(s, ML + 3.05, y + 1.02, 0.4, 0.18, "▼", size=8, color=BORDER_STRONG, align="c")

    # example narrative
    card(s, ML + 7.66, 1.80, 4.11, 3.38, fill=SURF2)
    tx(s, ML + 7.90, 1.98, 3.6, 0.22, "WHAT THE CAREGIVER READS", size=8, color=MUTED, bold=True, track=110)
    rich(s, ML + 7.90, 2.26, 3.64, 1.6, [
        {"runs": [{"t": "“Galvanic skin response rose to 8.4 µS while heart-rate variability fell to 19 ms — "
                        "the classic electrodermal signature of acute stress. Stress index is 0.74/1.00, "
                        "well above Margaret's calm baseline.”", "size": 9, "color": INK}], "line": 1.34}])
    hline(s, ML + 7.90, 3.92, 3.64, color=BORDER_STRONG, lw=0.75)
    tx(s, ML + 7.90, 4.02, 3.6, 0.22, "RECOMMENDED NEXT STEPS", size=8, color=MUTED, bold=True, track=110)
    bullets(s, ML + 7.90, 4.28, 3.64, 0.9,
            ["Call the wearer and confirm how she feels.",
             "Ask about pain, breathlessness or recent exertion.",
             "Escalate to the clinician if the index stays high for 20 minutes."],
            size=8.5, dot="•", gap=3, line=1.22, dot_color=ACCENT3)

    card(s, ML, 5.34, CW, 1.56, fill=SURF)
    tx(s, ML + 0.30, 5.52, 5.0, 0.24, "WHY A LANGUAGE LAYER — AND WHY IT MUST BE OPTIONAL",
       size=8, color=MUTED, bold=True, track=110)
    cols = [("Adoption", "Caregivers act on sentences, not on z-scores."),
            ("Auditability", "Every generated line can be traced back to stored evidence."),
            ("Continuity", "If the model provider is unavailable, detection still runs and alerts still write."),
            ("Cost control", "Narration is the only call that costs money per event — and it is bounded by alerts, not by readings.")]
    for i, (t, d) in enumerate(cols):
        rich(s, ML + 0.30 + (i % 2) * 5.90, 5.84 + (i // 2) * 0.46, 5.6, 0.44, [{"runs": [
            {"t": t + " — ", "size": 9, "bold": True, "color": ACCENT}, {"t": d, "size": 9, "color": TEXT2}], "line": 1.24}])
    footer(s, n, right="AI layer")

"""Deck section E — maturity, roadmap and the future-feature backlog."""
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE

from kit import *


def build(b):
    maturity(b)
    future_wearer(b)
    future_care(b)
    future_platform(b)


# ───────────────────────── 20 maturity & roadmap ───────────────────────
def maturity(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "05 / Roadmap", "From working prototype to validated product",
           "Three horizons. Nothing moves to “next” until the gate before it is passed.", num=n)

    horizons = [
        ("HORIZON 1", "Shipped today", "Working prototype", OK,
         ["Live telemetry over WebSocket", "8 conditions + inactivity watch",
          "Two-tier detection with calibration", "Caregiver dashboard: 6 views",
          "Safety escalation with GPS + log", "Device pairing and MQTT test",
          "Roles, sessions, seeded demo data", "QA + calibration suites green"]),
        ("HORIZON 2", "Next — 0–12 months", "Pilot-hardening", ACCENT3,
         ["Field hardware revision with bench validation", "Push, SMS and voice delivery integrations",
          "Native mobile app for the wearer", "Caseload / multi-wearer operator view",
          "Alert precision telemetry and tuning loop", "Battery and wear-time analytics",
          "Consent, retention and audit controls", "FHIR-ready data export"]),
        ("HORIZON 3", "Later — 12–36 months", "Platform", PURPLE,
         ["On-device equation engine at the edge", "Personal risk trajectory modelling",
          "Clinical review console for care teams", "Partner SDK and device-agnostic ingest",
          "Multi-condition chronic care programs", "Insurer and provider reporting packs",
          "Voice assistant and smart-home triggers", "Regulated pathway filing if evidence supports it"]),
    ]
    for i, (tag, title, sub, col, items) in enumerate(horizons):
        x = gx(i * 4)
        w = gw(4, 0.24)
        card(s, x, 1.74, w, 4.30, fill=SURF)
        rect(s, x, 1.74, w, 0.05, fill=col, radius=True, adj=0.5)
        tx(s, x + 0.24, 1.94, w - 0.5, 0.2, tag, size=7.5, color=col, bold=True, track=130)
        tx(s, x + 0.24, 2.18, w - 0.5, 0.28, title, size=14, color=INK, bold=True)
        tx(s, x + 0.24, 2.48, w - 0.5, 0.22, sub, size=9, color=MUTED)
        hline(s, x + 0.24, 2.80, w - 0.48, color=BORDER, lw=0.75)
        bullets(s, x + 0.24, 2.94, w - 0.5, 2.9, items, size=8.5, dot="·", gap=5, line=1.22, dot_color=col)

    card(s, ML, 6.16, CW, 0.74, fill=SURF2)
    tx(s, ML + 0.26, 6.28, 2.6, 0.22, "THE GATE BETWEEN HORIZONS", size=7.5, color=MUTED, bold=True, track=110)
    gates = [("H1 → H2", "Hardware accuracy validated on a bench and in 100+ wear-days"),
             ("H2 → H3", "Alert precision and retention targets met in pilot"),
             ("H3 → scale", "Economics and regulatory scope confirmed")]
    for i, (t, d) in enumerate(gates):
        rich(s, ML + 3.0 + i * 2.96, 6.24, 2.9, 0.5, [
            {"runs": [{"t": t + "  ", "size": 8.5, "bold": True, "color": ACCENT}], "line": 1.15},
            {"runs": [{"t": d, "size": 8, "color": TEXT2}], "line": 1.18}])
    footer(s, n, right="Roadmap")


# ──────────────────── 21 future features — wearer side ─────────────────
def future_wearer(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "05 / Roadmap", "Future features I — on the wrist",
           "Wearer-facing additions. Each one is a hypothesis with the gate that would justify it.", num=n)

    items = [
        ("On-device equation engine", "Run stress index, fall physics and core-temperature estimation directly on the ESP32 "
         "for offline alerts when the network drops.", "Gate: accuracy parity with the server path", ACCENT),
        ("Wear-time & battery intelligence", "Track daily wear-hours and charge cycles in-product, with a low-battery "
         "escalation path that reaches the caregiver.", "Gate: multi-day measured battery life", ACCENT3),
        ("Sleep, recovery and circadian context", "Turn overnight HRV, temperature and motion into a recovery picture "
         "that explains daytime alerts.", "Gate: clinician review of the derived metrics", PURPLE),
        ("Multi-day cellular band", "An LTE-M / eSIM variant for wearers with no home Wi-Fi — alerts travel even when "
         "the house does not.", "Gate: unit cost and power budget", OK),
        ("Wrist-worn form factor", "Move from a band prototype to a validated, washable, skin-safe wearable enclosure.",
         "Gate: DFM review and biocompatibility testing", DANGER),
        ("Wearer-facing companion app", "A deliberately simple wearer surface: status, dismiss, SOS, and nothing else.",
         "Gate: wearer usability testing at 70+", ACCENT),
        ("Cardiac rhythm screening", "Extend PPG analysis towards irregular-rhythm flags and AF burden estimates.",
         "Gate: reference ECG comparison study", ACCENT3),
        ("Medication and routine adherence", "Gentle nudges tied to the wearer's routine, correlated with physiological "
         "response afterwards.", "Gate: adherence improvement measured in pilot", PURPLE),
    ]
    for i, (t, d, gate, col) in enumerate(items):
        x = gx((i % 4) * 3)
        y = 1.76 + (i // 4) * 2.44
        w = gw(3, 0.22)
        card(s, x, y, w, 2.30, fill=SURF)
        rect(s, x, y, w, 0.045, fill=col, radius=True, adj=0.5)
        tx(s, x + 0.22, y + 0.22, w - 0.44, 0.56, t, size=11, color=INK, bold=True, line=1.15)
        tx(s, x + 0.22, y + 0.86, w - 0.44, 1.06, d, size=9, color=TEXT2, line=1.3)
        hline(s, x + 0.22, y + 1.94, w - 0.44, color=BORDER, lw=0.5)
        tx(s, x + 0.22, y + 2.02, w - 0.44, 0.24, gate, size=8, color=col, bold=True, line=1.15)
    footer(s, n, right="Future features · wearer")


# ────────────────── 22 future features — caregiver side ────────────────
def future_care(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "05 / Roadmap", "Future features II — on the caregiver's screen",
           "Everything that shortens the distance between an alert and a human response.", num=n)

    left = [
        ("Push, SMS and voice escalation", "Delivery receipts, retry ladders and a defined fallback order, "
         "so an urgent alert has more than one way to arrive.", "Gate: partner integration + delivery testing"),
        ("Caseload console for operators", "One screen for a care manager's entire roster: triage queue, severity "
         "sorting, per-wearer drill-down and shift handover notes.", "Gate: 2–3 signed pilot operators"),
        ("Family circle and delegation", "Time-boxed access for a sitter or a visiting nurse, with an audit trail "
         "showing who saw what.", "Gate: consent model + legal review"),
        ("Weekly narrative reports", "A written summary per wearer: what changed, how it trended, what was actioned — "
         "readable by a clinician.", "Gate: clinician feedback on usefulness"),
    ]
    right = [
        ("Care-team messaging", "Discuss an alert in context, attach the evidence and keep the thread attached to "
         "the incident record.", "Gate: pilot feedback on workflow value"),
        ("Scheduling and visit context", "Link readings to scheduled visits and to the staff member on duty, so an "
         "alert lands with the right person.", "Gate: rostering integration with a pilot partner"),
        ("Multilingual, accessible surfaces", "Localised explanations and a large-text mode for older caregivers — "
         "the same alert understood by everyone in the circle.", "Gate: translation review per market"),
        ("Explainable alert audit", "A reviewer view that shows why any historical alert fired, with its stored "
         "evidence and the thresholds in force at that moment.", "Gate: quality-review workflow in pilot"),
    ]
    for col_i, group in enumerate((left, right)):
        for i, (t, d, gate) in enumerate(group):
            x = gx(col_i * 6)
            y = 1.76 + i * 1.16
            w = gw(6, 0.22)
            card(s, x, y, w, 1.06, fill=SURF if i % 2 == 0 else SURF2)
            tx(s, x + 0.24, y + 0.16, w - 0.48, 0.26, t, size=11.5, color=INK, bold=True)
            tx(s, x + 0.24, y + 0.46, w - 0.48, 0.44, d, size=9, color=TEXT2, line=1.26)
            tx(s, x + w - 2.6, y + 0.16, 2.36, 0.26, gate, size=7.5, color=ACCENT3, align="r", line=1.15)
    card(s, ML, 6.36, CW, 0.54, fill=ACCENT, line=None)
    tx(s, ML + 0.26, 6.50, CW - 0.5, 0.26,
       "Delivery integrations are a partner dependency, not just a build task — escalation providers, local emergency "
       "numbering rules and consent policy differ per market and must be validated before any launch claim.",
       size=8.5, color=LIGHT)
    footer(s, n, right="Future features · caregiver")


# ───────────────── 23 future features — platform & clinical ────────────
def future_platform(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "05 / Roadmap", "Future features III — platform, data and evidence",
           "The bets that turn one product into an ecosystem — and the evidence that must come first.", num=n)

    rows = [["Capability", "What it adds", "Why it matters commercially", "Horizon"],
            ["Partner SDK & device-agnostic ingest", "Any sensor payload can be normalised into the same pipeline",
             "Turns competitors' hardware into distribution", "Later"],
            ["Clinical review console", "Clinician view of trends, evidence and alert history per wearer",
             "Unlocks provider channel and referral loops", "Later"],
            ["Personal risk trajectory", "Longitudinal baselines modelled into drift and deterioration signals",
             "Shifts from alerting to prediction — the defensible layer", "Later"],
            ["FHIR / HL7 export", "Structured, standards-based sharing with care systems",
             "Removes the largest integration objection from operators", "Next"],
            ["Reimbursement evidence pack", "Outcome reporting designed for payer questions",
             "Converts a subscription into a funded care cost", "Later"],
            ["Data governance programme", "Retention controls, consent ledger, least-privilege access, threat model",
             "Precondition for any health-system conversation", "Next"],
            ["Federated personalisation", "Improve equation priors across consenting wearers without moving raw data",
             "Better day-one accuracy for every new wearer", "Later"],
            ["Multi-condition programmes", "COPD, cardiac and post-surgical monitoring tracks on one platform",
             "Expands account value without new hardware", "Later"]]
    table(s, ML, 1.74, [2.90, 3.90, 3.85, 0.82], rows, row_h=0.44, head_h=0.34,
          size=8.5, head_size=7.5, bold_col0=True, align=["l", "l", "l", "c"],
          head_align=["l", "l", "l", "c"])

    card(s, ML, 6.06, CW, 0.84, fill=SURF2)
    tx(s, ML + 0.26, 6.16, 6.0, 0.22, "STANDING RULE FOR EVERY FUTURE FEATURE", size=7.5, color=MUTED, bold=True, track=110)
    rules = [("Evidence first", "No claim ships before the measurement that supports it."),
             ("Human in the loop", "Every escalation ends with a person, never with an automated decision."),
             ("Safety floors stay", "No roadmap item can move a clinical constant or a consent boundary.")]
    for i, (t, d) in enumerate(rules):
        rich(s, ML + 0.26 + i * 3.86, 6.42, 3.7, 0.42, [{"runs": [
            {"t": t + " — ", "size": 8.5, "bold": True, "color": ACCENT}, {"t": d, "size": 8.5, "color": TEXT2}], "line": 1.2}])
    footer(s, n, right="Future features · platform")

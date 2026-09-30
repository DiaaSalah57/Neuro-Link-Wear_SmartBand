"""Deck section A2 — problem, market, why now."""
from kit import *


def build(b):
    problem(b)
    market(b)
    whynow(b)


# ─────────────────────────────── 04 problem ────────────────────────────
def problem(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "01 / Problem", "Critical health changes happen between check-ins",
           "Care is delivered in snapshots. A short visit, a phone call, a reading taken once — "
           "while the signals that matter are continuous.", num=n)

    gaps = [
        ("Signals lose their context", "A heart rate of 96 bpm is unremarkable on a walk and alarming at rest. "
         "Single readings, taken alone, cannot separate the two.", ACCENT),
        ("Early warning is easy to miss", "Fever, fatigue, panic and low oxygen usually begin as subtle trends — "
         "a slow drift that a person feels only after the fact.", PURPLE),
        ("The response path is improvised", "When something does go wrong at 3 a.m., the people who care are "
         "called in an order nobody wrote down.", DANGER),
    ]
    y = 1.86
    for i, (t, d, col) in enumerate(gaps):
        card(s, ML, y, 6.62, 1.30, fill=SURF)
        oval(s, ML + 0.26, y + 0.30, 0.60, 0.60, SURF3)
        tx(s, ML + 0.26, y + 0.42, 0.60, 0.36, f"{i+1}", size=15, color=col, bold=True, align="c")
        tx(s, ML + 1.02, y + 0.22, 5.3, 0.28, t, size=12.5, color=INK, bold=True)
        tx(s, ML + 1.02, y + 0.54, 5.3, 0.66, d, size=9.5, color=TEXT2, line=1.3)
        y += 1.40

    card(s, ML, y, 6.62, 0.88, fill=ACCENT, line=None)
    tx(s, ML + 0.26, y + 0.18, 6.1, 0.26,
       "THE INSIGHT THAT SHAPES THE PRODUCT", size=8, color=LAV, bold=True, track=120)
    tx(s, ML + 0.26, y + 0.46, 6.1, 0.34,
       "The missing piece is not another measurement. It is context, timing and a response that already exists.",
       size=10.5, color=LIGHT, line=1.25)

    # right column: the daily reality
    x = 7.68
    card(s, x, 1.86, 4.86, 2.86, fill=SURF)
    tx(s, x + 0.28, 2.06, 4.3, 0.24, "A DAY IN THE CURRENT MODEL", size=8, color=MUTED, bold=True, track=110)
    timeline = [("07:30", "Morning check-in call", "“I'm fine.” — no data"),
                ("13:10", "Blood pressure at the clinic", "one reading, archived"),
                ("18:40", "A slow walk, breathlessness", "not noticed by anyone"),
                ("02:15", "Night-time bathroom fall", "no alert, no context, no log")]
    ty = 2.44
    for i, (t, label, sub) in enumerate(timeline):
        col = DANGER if i == 3 else (ACCENT3 if i == 2 else MUTED)
        dot(s, x + 0.30, ty + 0.055, 0.09, col)
        if i < len(timeline) - 1:
            vline(s, x + 0.342, ty + 0.20, 0.44, color=BORDER_STRONG, lw=0.75)
        tx(s, x + 0.52, ty, 0.72, 0.22, t, size=9, color=col, bold=True)
        tx(s, x + 1.28, ty - 0.02, 3.3, 0.24, label, size=10, color=INK, bold=True)
        tx(s, x + 1.28, ty + 0.22, 3.3, 0.22, sub, size=8.5, color=MUTED)
        ty += 0.58

    card(s, x, 4.84, 4.86, 2.10, fill=SURF2)
    tx(s, x + 0.28, 5.04, 4.3, 0.24, "WHAT FAMILIES ACTUALLY NEED", size=8, color=MUTED, bold=True, track=110)
    bullets(s, x + 0.28, 5.36, 4.3, 1.5,
            [("A trend, not a number. ", "“Her resting pulse has been 12 bpm higher for two days.”"),
             ("A threshold built for one body. ", "Her normal is not the population average."),
             ("A path to a human. ", "When it matters, someone is reached — and it is logged.")],
            size=9, dot="·", gap=5, line=1.28)
    footer(s, n, right="Problem")


# ─────────────────────────────── 05 market ─────────────────────────────
def market(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "01 / Market", "Who pays, and why now",
           "Three segments, one sensing platform — the first commercial wedge stays narrow on purpose.",
           num=n)

    # three market blocks
    blocks = [
        ("BEACHHEAD", "Aging-at-home households", "Family caregiver households with one wearer and 1–3 trusted contacts. "
         "Direct subscription paid by a son or daughter.", ["~1 in 3 older adults wants to stay home",
                                                            "Informal family care is the default safety net"], ACCENT),
        ("EXPANSION", "Home care & senior living", "Multi-wearer dashboards for professional care teams, "
         "paid pilots, staff workflow and reporting.", ["Staff-to-resident alerting and audit trail",
                                                        "Buyer already budgets for monitoring"], PURPLE),
        ("LONG TERM", "Remote care ecosystem", "Provider, payer and employer relationships once detection "
         "quality and integration are proven.", ["Chronic-condition remote monitoring",
                                                 "Escalation evidence unlocks reimbursement"], ACCENT3),
    ]
    for i, (tag, title, body, points, col) in enumerate(blocks):
        x = gx(i * 4, )
        card(s, x, 1.74, gw(4, 0.24), 3.00, fill=SURF)
        tx(s, x + 0.26, 1.94, 3.4, 0.22, tag, size=8, color=col, bold=True, track=130)
        tx(s, x + 0.26, 2.20, gw(4, 0.7), 0.34, title, size=14, color=INK, bold=True, line=1.14)
        tx(s, x + 0.26, 2.66, gw(4, 0.72), 1.0, body, size=9.5, color=TEXT2, line=1.32)
        hline(s, x + 0.26, 3.72, gw(4, 0.72), color=BORDER, lw=0.75)
        bullets(s, x + 0.26, 3.86, gw(4, 0.72), 0.7, points, size=8.5, dot="·", gap=4, dot_color=col)

    # bottom: why now + scale illustration
    card(s, ML, 4.92, 6.62, 1.98, fill=SURF2)
    tx(s, ML + 0.26, 5.12, 6.0, 0.24, "WHY NOW — FIVE ENABLERS", size=8, color=MUTED, bold=True, track=120)
    enablers = [("Sensor economics", "PPG, GSR, IMU and temperature modules are commodity parts."),
                ("Edge compute", "An ESP32-class chip runs feature extraction and thresholds on the wrist."),
                ("Transparent AI", "Equation-based models pass comprehension review where black boxes stall."),
                ("Remote-care demand", "Care-at-a-distance is now a mainstream family arrangement."),
                ("Open connectivity", "MQTT over Wi-Fi plus a web dashboard removes the app-store gate.")]
    positions = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]
    for i, (t, d) in enumerate(enablers):
        c, r = positions[i]
        rich(s, ML + 0.26 + c * 3.30, 5.42 + r * 0.47, 3.12, 0.46, [
            {"runs": [{"t": t + " — ", "size": 8.5, "bold": True, "color": INK},
                      {"t": d, "size": 8.5, "color": TEXT2}], "line": 1.22}])

    card(s, 7.68, 4.92, 4.86, 1.98, fill=ACCENT, line=None)
    tx(s, 7.94, 5.12, 4.3, 0.24, "SCALE ILLUSTRATION — NOT A TAM CLAIM", size=8, color=LAV, bold=True, track=110)
    for i, (v, l) in enumerate([("100,000", "paid wearer accounts"), ("$14.4M", "annual subscription revenue at $12/month"),
                                ("$14.9M", "one-off device revenue at $149 ASP")]):
        rich(s, 7.94 + i * 1.52, 5.46, 1.5, 0.7, [
            {"runs": [{"t": v, "size": 15, "bold": True, "color": LIGHT}], "line": 1.05},
            {"runs": [{"t": l, "size": 8, "color": LIGHT2}], "space_before": 2, "line": 1.2}])
    tx(s, 7.94, 6.26, 4.3, 0.5,
       "Illustrative capacity case to show model mechanics only. Launch geography, eligible base, "
       "reimbursement and pricing require validation before any market-size statement.",
       size=8, color=LIGHT2, line=1.25)
    footer(s, n, right="Market")


# ─────────────────────────────── 06 why now ────────────────────────────
def whynow(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "01 / Market", "The timing argument in one page", num=n)

    left = [
        ("The demographic curve is not a forecast", "It is arithmetic. Aging populations and "
         "caregiving shortages are policy problems already being funded."),
        ("Consumer wearables normalised the wrist", "The behaviour change — charging a device, "
         "sleeping with it, reading its app — has already happened."),
        ("But consumer devices stop at data", "Rings and watches report. They do not run a "
         "caregiver workflow, escalate to a contact or log a dispatch."),
        ("Clinical-grade transparency is now a requirement", "Care organisations ask “why did it "
         "alert?” before they ask “how accurate is it?” Explainability is a sales asset."),
    ]
    y = 1.74
    for i, (t, d) in enumerate(left):
        card(s, ML, y, 6.62, 1.20, fill=SURF if i % 2 == 0 else SURF2)
        tx(s, ML + 0.26, y + 0.20, 6.1, 0.26, t, size=11.5, color=INK, bold=True)
        tx(s, ML + 0.26, y + 0.52, 6.1, 0.58, d, size=9.5, color=TEXT2, line=1.3)
        y += 1.32

    x = 7.68
    card(s, x, 1.74, 4.86, 2.42, fill=SURF)
    tx(s, x + 0.28, 1.94, 4.3, 0.24, "THE GAP WE OCCUPY", size=8, color=MUTED, bold=True, track=120)
    rows = [("Fitness trackers", "Data, no care workflow", MUTED),
            ("Medical alert buttons", "Reactive, one-way, no context", MUTED),
            ("Clinical monitoring", "Effective but institution-bound", MUTED),
            ("NeuroLink Wear", "Continuous sensing + explanation + escalation", ACCENT)]
    ry = 2.34
    for label, desc, col in rows:
        last = col == ACCENT
        rich(s, x + 0.28, ry, 4.3, 0.44, [
            {"runs": [{"t": label + "  ", "size": 10, "bold": True, "color": INK if last else TEXT2},
                      {"t": desc, "size": 9, "color": col if last else MUTED}], "line": 1.22}])
        if not last:
            hline(s, x + 0.28, ry + 0.42, 4.3, color=BORDER, lw=0.5)
        ry += 0.54

    card(s, x, 4.30, 4.86, 2.60, fill=SURF2)
    tx(s, x + 0.28, 4.50, 4.3, 0.24, "MARKET EVIDENCE TO COLLECT IN THE PILOT", size=8, color=MUTED, bold=True, track=110)
    bullets(s, x + 0.28, 4.86, 4.3, 1.9,
            ["Willingness to pay: family subscription vs. device-only.",
             "Attach rate inside a home-care operator's caseload.",
             "Cost to serve per wearer per month (support dominates).",
             "Reimbursement pathway questions for the remote-care segment.",
             "Churn after the first false alert."],
            size=9.5, dot="→", gap=6, dot_color=ACCENT)
    footer(s, n, right="Market")

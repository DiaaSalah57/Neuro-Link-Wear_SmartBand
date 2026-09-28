"""Deck section A1 — cover, agenda, executive summary."""
from pptx.enum.dml import MSO_LINE_DASH_STYLE

from kit import *


def build(b):
    cover(b)
    agenda(b)
    summary(b)


# ─────────────────────────────── 01 cover ──────────────────────────────
def cover(b):
    s = slide(b.prs, BG)
    b.num()
    # soft lavender gradient band
    rect(s, 0, 0, W, H, fill=SURF3, radius=False)
    rect(s, 0, 0, W, 4.4, fill=BG, radius=False)

    rect(s, ML, 0.82, 0.42, 0.06, fill=ACCENT3, radius=True, adj=0.5)
    tx(s, ML, 1.00, 9.0, 0.30, "NEUROLINK WEAR  ·  SMART BAND HEALTH & SAFETY PLATFORM",
       size=10, color=PURPLE, bold=True, track=150)
    tx(s, ML, 1.40, 7.6, 1.42,
       "Predictive health intelligence,\nworn every day.", size=36, color=INK, bold=True, line=1.06)
    tx(s, ML, 2.68, 6.9, 1.15,
       "One sensing band, one explainable AI engine and one caregiver dashboard — built to catch "
       "a health change between check-ins and turn it into a human response.",
       size=12.5, color=TEXT2, line=1.38)
    tx(s, ML, 3.86, 6.9, 1.4,
       "Real-time vitals  ·  eight monitored conditions  ·  per-wearer calibration  ·  "
       "fall detection with GPS  ·  emergency dispatch  ·  caregiver back-office",
       size=10, color=MUTED, line=1.5)

    # signature vitals panel
    card(s, 8.30, 1.40, 4.24, 4.54, fill=SURF)
    tx(s, 8.55, 1.64, 3.74, 0.24, "LIVE WEARER SIGNAL", size=8, color=MUTED, bold=True, track=120)
    tx(s, 8.55, 1.92, 2.4, 0.24, "Margaret T. · 78 · at home", size=8.5, color=MUTED)
    chip(s, 11.28, 1.88, 1.02, 0.28, "● LIVE", fg=OK, bgc=OK_BG, size=8, track=30)

    vitals = [("Heart rate", "72", "bpm", ACCENT, [70, 72, 71, 74, 73, 72, 75, 73, 72, 71, 72, 72]),
              ("Blood oxygen", "97", "%", ACCENT3, [97, 97, 96, 97, 98, 97, 97, 96, 97, 97, 97, 97]),
              ("Skin temp", "36.4", "°C", PURPLE, [36.3, 36.4, 36.4, 36.5, 36.4, 36.4, 36.3, 36.4, 36.4, 36.4, 36.5, 36.4]),
              ("Stress index", "0.28", "/1", ACCENT2, [.25, .27, .26, .3, .28, .26, .27, .29, .28, .27, .26, .28])]
    y = 2.30
    for label, val, unit, col, series in vitals:
        tx(s, 8.55, y, 2.0, 0.25, label, size=9.5, color=TEXT2, anchor="m")
        rich(s, 10.62, y - 0.06, 1.6, 0.32, [{"align": "r", "runs": [
            {"t": val, "size": 14, "bold": True, "color": col},
            {"t": " " + unit, "size": 8.5, "color": MUTED}]}])
        spark(s, 8.55, y + 0.30, 3.68, 0.28, series, color=col, lw=1.3)
        hline(s, 8.55, y + 0.70, 3.68, color=BORDER, lw=0.5)
        y += 0.74

    chip(s, 8.55, 5.42, 3.68, 0.32,
         "8 conditions monitored · 2-tier safety rules · 24 h inactivity watch",
         fg=TEXT2, bgc=SURF2, size=8, track=10)

    # bottom meta line
    hline(s, ML, 6.28, CW, color=BORDER_STRONG, lw=0.75)
    for i, (k, v) in enumerate([("PROPOSITION", "Device + AI + care workflow"),
                                ("FIRST MARKET", "Aging at home"),
                                ("STAGE", "Working software prototype"),
                                ("ASK", "$1.5M pre-seed · pilot-led")]):
        x = ML + i * (CW / 4)
        tx(s, x, 6.46, CW / 4 - 0.2, 0.22, k, size=7.5, color=MUTED, bold=True, track=110)
        tx(s, x, 6.70, CW / 4 - 0.2, 0.26, v, size=10, color=INK, bold=True)
    tx(s, ML, 7.14, CW, 0.2,
       "Investor & technical review deck · September 2026 · financials are illustrative planning scenarios",
       size=7.5, color=MUTED)


# ─────────────────────────────── 02 agenda ─────────────────────────────
def agenda(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "Contents", "Nine questions this deck answers",
           "Each section is built to be read on its own — every figure carries its source and status.",
           num=n)
    items = [
        ("01", "Problem", "The monitoring gap between check-ins", OK),
        ("02", "Market", "Who pays, and why now", OK),
        ("03", "Solution", "Sense → understand → respond", OK),
        ("04", "Product", "Band, dashboard, safety workflow", OK),
        ("05", "Intelligence", "Equations, calibration, LLM layer", OK),
        ("06", "Audience", "Segments, personas, beachhead", OK),
        ("07", "Roadmap", "Shipped, next, future features", ACCENT3),
        ("08", "Business", "Model, pricing, go-to-market", ACCENT3),
        ("09", "Financials", "5-year plan, break-even, ask", ACCENT3),
    ]
    x0, y0 = ML, 2.05
    cw, ch = 3.84, 1.16
    for i, (num, title, sub, col) in enumerate(items):
        r, c = divmod(i, 3)
        x = x0 + c * (cw + 0.13)
        y = y0 + r * (ch + 0.14)
        card(s, x, y, cw, ch, fill=SURF)
        tx(s, x + 0.22, y + 0.18, 0.9, 0.26, num, size=9, color=col, bold=True, track=90)
        tx(s, x + 0.22, y + 0.44, cw - 0.44, 0.3, title, size=14, color=INK, bold=True)
        tx(s, x + 0.22, y + 0.76, cw - 0.44, 0.3, sub, size=9, color=MUTED, line=1.2)
    tx(s, ML, 6.34, CW, 0.3,
       "Status legend used throughout:  ✔ shipped in the current build   ·   ◦ roadmap candidate (not committed)",
       size=9, color=MUTED, track=10)
    footer(s, n, right="Contents")


# ──────────────────────── 03 executive summary ─────────────────────────
def summary(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "Executive summary", "What exists, what is next, what it is worth", num=n)
    tx(s, ML, 1.42, 7.5, 0.24,
       "WORKING SOFTWARE PROTOTYPE — QA + CALIBRATION SUITES GREEN (141 · 74 · 17 CHECKS)",
       size=8, color=PURPLE, bold=True, track=110)

    col_w = 5.72
    facts = [
        ("Real-time monitoring", "Heart rate, blood oxygen, skin temperature, GSR stress index and IMU motion streamed live — 2-second WebSocket updates, 8 conditions evaluated on every reading.", OK),
        ("Explainable AI, no training set", "Physiology equations plus per-wearer calibration replace a black box; every alert cites the numbers that triggered it.", ACCENT3),
        ("Safety floors that never move", "Two-tier rules: clinical absolutes OR the wearer's own σ-deviation. Personalisation can only add sensitivity.", PURPLE),
        ("End-to-end escalation", "Incident timeline, live GPS map, dispatch log and one-click emergency-contact delivery in one safety view.", DANGER),
        ("Caregiver back-office built in", "Contacts, device pairing with a staged MQTT connection test, thresholds, calibration wizard, roles and 30-day sessions.", ACCENT),
        ("Measured, not asserted", "141-check QA battery, 74-check calibration suite, 17 DOM checks — all passing, all re-runnable on demand.", OK),
    ]
    top = 1.72
    for i, (t, d, col) in enumerate(facts):
        r, c = divmod(i, 2)
        y = top + r * 1.34
        x = ML if c == 0 else ML + col_w + 0.34
        card(s, x, y, col_w, 1.26, fill=SURF)
        rect(s, x + 0.22, y + 0.22, 0.045, 0.72, fill=col, radius=True, adj=0.5)
        tx(s, x + 0.40, y + 0.20, col_w - 0.62, 0.26, t, size=11.5, color=INK, bold=True)
        tx(s, x + 0.40, y + 0.52, col_w - 0.62, 0.64, d, size=9.5, color=TEXT2, line=1.3)

    y = top + 3 * 1.34
    card(s, ML, y, col_w, 1.04, fill=SURF2)
    tx(s, ML + 0.22, y + 0.14, col_w - 0.44, 0.24, "STATUS HONESTY — WHAT IS NOT PROVEN YET",
       size=8, color=MUTED, bold=True, track=110)
    tx(s, ML + 0.22, y + 0.42, col_w - 0.44, 0.54,
       "Wearable is prototype-grade hardware; alert precision, battery life, adherence and regulatory scope "
       "are hypotheses that only a field pilot can settle.", size=9, color=TEXT2, line=1.28)

    card(s, ML + col_w + 0.34, y, col_w, 1.04, fill=ACCENT, line=None)
    tx(s, ML + col_w + 0.56, y + 0.13, col_w - 0.44, 0.24, "THE ASK", size=8, color=LAV, bold=True, track=120)
    rich(s, ML + col_w + 0.56, y + 0.40, col_w - 0.44, 0.58, [
        {"runs": [{"t": "$1.5M pre-seed", "size": 14, "bold": True, "color": LIGHT}], "line": 1.15},
        {"runs": [{"t": "~18 months to a validated, pilot-ready product — 2–3 pilot partners, "
                        "100–150 wearers, measured precision and response time.",
                   "size": 8.5, "color": LIGHT2}], "space_before": 2, "line": 1.24}])
    footer(s, n, right="Executive summary")

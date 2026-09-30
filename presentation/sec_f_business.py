"""Deck section F — business model, unit economics, go-to-market and pilot plan."""
from pptx.enum.shapes import MSO_SHAPE

from kit import *


def build(b):
    bmodel(b)
    unit(b)
    gtm(b)
    pilot(b)


# ────────────────────────── 24 business model ──────────────────────────
def bmodel(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "06 / Business", "Hardware opens the account. Software keeps it.",
           "Device margin funds acquisition; subscription and operator contracts fund the company.", num=n)

    streams = [
        ("DEVICE SALE", "$149", "one-time", "Band, charging cradle and starter kit. Priced at roughly "
         "1.7× unit cost — deliberately not the profit centre.", ACCENT),
        ("CONSUMER SUBSCRIPTION", "$12 / month", "recurring", "AI insights, unlimited history, caregiver circle "
         "and safety escalation. The primary revenue engine.", ACCENT3),
        ("OPERATOR LICENCE", "$9–18 / wearer / mo", "contract", "Caseload console, staff workflow, reporting "
         "and audit trail for home-care and living operators.", PURPLE),
        ("EVIDENCE & INTEGRATION", "Pilot fee + licence", "strategic", "Paid pilots with providers and payers that "
         "convert to integration contracts once detection quality is proven.", OK),
    ]
    for i, (tag, price, kind, body, col) in enumerate(streams):
        x = gx(i * 3)
        w = gw(3, 0.22)
        card(s, x, 1.76, w, 2.30, fill=SURF)
        rect(s, x, 1.76, w, 0.05, fill=col, radius=True, adj=0.5)
        tx(s, x + 0.22, 1.96, w - 0.44, 0.2, tag, size=7.5, color=col, bold=True, track=100)
        tx(s, x + 0.22, 2.18, w - 0.44, 0.44, price, size=16, color=INK, bold=True, line=1.05)
        tx(s, x + 0.22, 2.62, w - 0.44, 0.2, kind, size=8.5, color=MUTED, track=60)
        hline(s, x + 0.22, 2.88, w - 0.44, color=BORDER, lw=0.75)
        tx(s, x + 0.22, 3.02, w - 0.44, 0.94, body, size=8.5, color=TEXT2, line=1.3)

    card(s, ML, 4.22, 5.86, 2.68, fill=SURF2)
    tx(s, ML + 0.26, 4.40, 5.3, 0.24, "WHY A SUBSCRIPTION IS DEFENSIBLE HERE", size=8, color=MUTED, bold=True, track=110)
    bullets(s, ML + 0.26, 4.72, 5.3, 2.0,
            [("Value is continuous, not transactional. ", "The safety net only exists while the service runs."),
             ("Switching cost compounds. ", "Calibration baselines and history belong to this wearer."),
             ("Marginal cost is low. ", "Storage and narration per wearer are bounded by alerts, not readings."),
             ("Operators need the software. ", "The hardware alone cannot serve a caseload."),
             ("Price sits below the alternative. ", "A private caregiver hour costs far more than a month.")],
            size=9, dot="·", gap=6, line=1.26)

    card(s, ML + 6.10, 4.22, 5.67, 2.68, fill=SURF)
    tx(s, ML + 6.36, 4.40, 5.1, 0.24, "PRICING PRINCIPLES WE WILL TEST IN PILOT", size=8, color=MUTED, bold=True, track=110)
    principles = [("Annual prepay", "discount to reduce churn and fund hardware"),
                  ("Family circle", "up to 3 contacts included, more as an add-on"),
                  ("Operator tiering", "per-wearer price steps down with volume"),
                  ("Hardware bundling", "band free on a 24-month subscription?"),
                  ("No charge for alerts", "monetising safety events would be indefensible")]
    py = 4.74
    for t, d in principles:
        rich(s, ML + 6.36, py, 5.1, 0.42, [{"runs": [
            {"t": t + " — ", "size": 9, "bold": True, "color": ACCENT}, {"t": d, "size": 9, "color": TEXT2}], "line": 1.24}])
        py += 0.42
    footer(s, n, right="Business model")


# ────────────────────────── 25 unit economics ──────────────────────────
def unit(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "06 / Business", "Unit economics: where the money is made and lost",
           "Illustrative base-case assumptions for discussion — not validated costs.", num=n)

    # device unit economics waterfall
    card(s, ML, 1.76, 5.86, 2.86, fill=SURF)
    tx(s, ML + 0.26, 1.94, 5.3, 0.24, "DEVICE UNIT — BASE CASE", size=8, color=MUTED, bold=True, track=110)
    rows = [["Line", "Amount", "Note"],
            ["Average selling price", "$149", "consumer, one-time"],
            ["Bill of materials", "−$62", "band, sensors, ESP32, enclosure"],
            ["Assembly and test", "−$12", "contract manufacturer"],
            ["Packaging and freight", "−$8", "consumer retail pack"],
            ["Warranty and returns reserve", "−$8", "3 % return assumption"],
            ["Gross contribution per device", "$59", "39 % gross margin"]]
    table(s, ML + 0.26, 2.22, [2.30, 1.06, 1.92], rows, row_h=0.28, head_h=0.26,
          size=8.5, head_size=7.5, bold_col0=True, align=["l", "r", "l"], head_align=["l", "r", "l"])
    tx(s, ML + 0.26, 4.22, 5.3, 0.24,
       "Target: $52 device COGS at 10k units, improving with procurement scale.", size=8, color=ACCENT)

    card(s, ML + 6.10, 1.76, 5.67, 2.86, fill=SURF)
    tx(s, ML + 6.36, 1.94, 5.1, 0.24, "SUBSCRIPTION UNIT — PER WEARER, PER MONTH", size=8, color=MUTED, bold=True, track=110)
    rows2 = [["Line", "Amount", "Note"],
             ["List price", "$12.00", "consumer tier"],
             ["Cloud, storage and narration", "−$0.85", "bounded by alerts, not readings"],
             ["Support and service", "−$1.60", "the real cost driver"],
             ["Payment, tax, bad debt", "−$0.55", "≈ 4.5 % of revenue"],
             ["Contribution per wearer / month", "$9.00", "75 % gross margin"],
             ["Blended CAC target", "$85–140", "payback in 10–16 months"]]
    table(s, ML + 6.36, 2.22, [2.44, 1.02, 1.62], rows2, row_h=0.28, head_h=0.26,
          size=8.5, head_size=7.5, bold_col0=True, align=["l", "r", "l"], head_align=["l", "r", "l"])
    rich(s, ML + 6.36, 4.24, 5.1, 0.28, [{"runs": [
        {"t": "LTV : CAC ", "size": 9, "bold": True, "color": INK},
        {"t": "≈ 3.2× at a 24-month average life, before the device contribution is counted.", "size": 8.5, "color": TEXT2}]}])

    # economics of the account
    card(s, ML, 4.82, CW, 1.98, fill=SURF2)
    tx(s, ML + 0.26, 5.00, 6.0, 0.24, "THE FOUR NUMBERS THAT DECIDE THIS BUSINESS",
       size=8, color=MUTED, bold=True, track=110)
    metrics = [("Alert precision", "> 90 %", "alerts that a caregiver judges actionable", ACCENT),
               ("Time to acknowledgement", "< 5 min", "median, from alert to human response", DANGER),
               ("Wear adherence", "> 20 h/day", "sustained after the first month", ACCENT3),
               ("Support cost per wearer", "< $1.60", "the margin line most likely to break", WARN)]
    for i, (t, v, d, col) in enumerate(metrics):
        x = ML + 0.26 + i * 2.86
        tx(s, x, 5.30, 2.6, 0.2, t, size=8, color=col, bold=True, track=60)
        tx(s, x, 5.52, 2.6, 0.36, v, size=18, color=INK, bold=True, line=1.05)
        tx(s, x, 5.96, 2.66, 0.56, d, size=8.5, color=TEXT2, line=1.26)
    footer(s, n, right="Unit economics")


# ─────────────────────────── 26 go-to-market ───────────────────────────
def gtm(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "06 / Business", "Prove the loop in a narrow pilot, then scale",
           "Success means a trusted response loop, repeat use, and a cost to serve that survives scale.", num=n)

    phases = [
        ("0–3 MONTHS", "PILOT DESIGN", ["2–3 pilot partners signed", "100–150 target wearers",
                                        "Caregiver + wearer interviews", "Safety review of escalation rules"], ACCENT),
        ("3–9 MONTHS", "CONTROLLED PILOT", ["Pre-registered endpoints", "Adherence and alert telemetry",
                                            "Weekly service feedback loop", "Shadow-mode comparison of thresholds"], ACCENT3),
        ("9–18 MONTHS", "REPEATABLE SALES", ["Convert paid sites", "Family-plan pricing tests",
                                             "Channel and support playbook", "Second vertical preparation"], PURPLE),
    ]
    for i, (when, title, items, col) in enumerate(phases):
        x = gx(i * 4)
        w = gw(4, 0.24)
        card(s, x, 1.76, w, 2.42, fill=SURF)
        rect(s, x, 1.76, 0.045, 2.42, fill=col, radius=True, adj=0.5)
        tx(s, x + 0.26, 1.94, w - 0.5, 0.2, when, size=7.5, color=col, bold=True, track=110)
        tx(s, x + 0.26, 2.16, w - 0.5, 0.28, title, size=13, color=INK, bold=True)
        bullets(s, x + 0.26, 2.54, w - 0.5, 1.5, items, size=9, dot="·", gap=4, line=1.24, dot_color=col)

    # channels
    card(s, ML, 4.34, 5.86, 2.56, fill=SURF)
    tx(s, ML + 0.26, 4.52, 5.3, 0.24, "CHANNELS, IN ORDER OF INTENT", size=8, color=MUTED, bold=True, track=110)
    channels = [("1", "Direct pilot conversions", "The first revenue comes from sites that already tested the product."),
                ("2", "Family caregiver communities", "Support groups, condition associations and referral from existing families."),
                ("3", "Home-care operators", "Caseload deployments where one contract places many wearers."),
                ("4", "Clinician referral", "Discharge and chronic-care follow-up, once the evidence pack exists."),
                ("5", "Pharmacy and retail", "Late-stage consumer reach; expensive before proof.")]
    cy = 4.84
    for i, (idx, t, d) in enumerate(channels):
        rich(s, ML + 0.26, cy, 5.3, 0.38, [{"runs": [
            {"t": idx + "  ", "size": 9, "bold": True, "color": ACCENT},
            {"t": t + " — ", "size": 9, "bold": True, "color": INK},
            {"t": d, "size": 9, "color": TEXT2}], "line": 1.22}])
        cy += 0.40

    card(s, ML + 6.10, 4.34, 5.67, 2.56, fill=ACCENT, line=None)
    tx(s, ML + 6.36, 4.52, 5.1, 0.24, "PILOT SCORECARD — WHAT WE MEASURE", size=8, color=LAV, bold=True, track=110)
    score = [("Wear-days / active days", "adherence in real life"),
             ("Battery days per charge", "the form-factor gate"),
             ("Alert precision (PPV)", "did the alert deserve action?"),
             ("False alerts per day", "the churn driver"),
             ("Time to acknowledgement", "is the loop actually closed?"),
             ("Contact delivery success", "does the escalation path work?"),
             ("Willingness to pay", "price sensitivity, tested directly")]
    for i, (t, d) in enumerate(score):
        cx = ML + 6.36 + (i % 2) * 2.72
        cyy = 4.84 + (i // 2) * 0.44
        rich(s, cx, cyy, 2.66, 0.46, [
            {"runs": [{"t": t, "size": 8.5, "bold": True, "color": LIGHT}], "line": 1.15},
            {"runs": [{"t": d, "size": 7.5, "color": LIGHT2}], "line": 1.15}])
    tx(s, ML + 6.36, 6.64, 5.1, 0.22,
       "No signed partner is represented here — the pilot funnel is the immediate workstream.",
       size=8, color=LIGHT2)
    footer(s, n, right="Go to market")


# ───────────────────────────── 27 pilot plan ───────────────────────────
def pilot(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "06 / Business", "The pilot is the product: an instrument, not a demo",
           "Designed to surface failure modes — a pilot that only proves the happy path wastes the money.", num=n)

    # 3 month timeline bars
    card(s, ML, 1.74, CW, 2.22, fill=SURF)
    tx(s, ML + 0.26, 1.92, 8.0, 0.24, "18-MONTH RUNWAY PLAN — WHAT HAPPENS WHEN",
       size=8, color=MUTED, bold=True, track=110)
    # month ruler
    month_w = (CW - 0.52) / 18
    rx = ML + 0.26
    for m in range(19):
        if m % 3 == 0 and m < 18:
            tx(s, rx + m * month_w - 0.2, 2.22, 0.6, 0.2, f"M{m}", size=7, color=MUTED, align="c")
    hline(s, ML + 0.26, 2.46, CW - 0.52, color=BORDER, lw=0.75)
    tracks = [("Hardware verification & bench validation", 0, 6, ACCENT),
              ("Pilot design, safety review, partner onboarding", 1, 5, ACCENT3),
              ("Controlled pilot with 100–150 wearers", 5, 8, PURPLE),
              ("Evidence pack, delivery integrations, security", 6, 8, OK),
              ("Repeatable sales playbook and second vertical", 12, 6, DANGER)]
    ty = 2.58
    for label, start, length, col in tracks:
        tx(s, ML + 0.26, ty, 4.9, 0.24, label, size=8.5, color=TEXT2, anchor="m")
        hbar(s, ML + 5.30, ty + 0.055, CW - 5.56, 0.13, 1.0, color=SURF3)
        rect(s, ML + 5.30 + start * ((CW - 5.56) / 18), ty + 0.055, length * ((CW - 5.56) / 18), 0.13,
             fill=col, radius=True, adj=0.5)
        ty += 0.28

    # milestones + risk columns
    card(s, ML, 4.16, 5.86, 2.74, fill=SURF2)
    tx(s, ML + 0.26, 4.34, 5.3, 0.24, "PILOT DESIGN — THE NON-NEGOTIABLES", size=8, color=MUTED, bold=True, track=110)
    bullets(s, ML + 0.26, 4.66, 5.3, 2.0,
            [("Pre-register the endpoints. ", "Precision, sensitivity, time-to-response — defined before data."),
             ("Shadow mode first. ", "Run detection silently against reference measurements before alerting families."),
             ("Human review of every alert. ", "A clinician or nurse adjudicates each event in the first weeks."),
             ("Instrument the awkward cases. ", "Charging, showering, sleeping, travel — adherence lives there."),
             ("Consent and retention from day one. ", "The pilot is where the privacy model must prove itself.")],
            size=9, dot="·", gap=6, line=1.26)

    card(s, ML + 6.10, 4.16, 5.67, 2.74, fill=SURF)
    tx(s, ML + 6.36, 4.34, 5.1, 0.24, "FAILURE MODES THE DESIGN MUST CATCH", size=8, color=MUTED, bold=True, track=110)
    rows = [["Risk", "Design response"],
            ["Measurement bias / sensor noise", "Bench testing against reference instruments; per-signal quality checks"],
            ["False alerts erode trust", "Shadow mode, adjudication, tuning loop with weekly review"],
            ["Battery or wear abandonment", "Daily wear-time telemetry; usability interviews; charger redesign"],
            ["Emergency delivery failure", "Delivery receipts, retries, fallback contacts, honest disclaimers"],
            ["Privacy or security incident", "Least privilege, retention limits, threat model before pilot start"],
            ["Regulatory scope drift", "Define intended use as wellness / safety support, not diagnosis"]]
    table(s, ML + 6.36, 4.62, [2.30, 2.85], rows, row_h=0.36, head_h=0.26, size=8, head_size=7.5,
          bold_col0=True, align=["l", "l"])
    footer(s, n, right="Pilot plan")

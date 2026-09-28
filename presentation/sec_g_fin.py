"""Deck section G — financial plan, P&L, financing ask, risks and closing."""
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE

from kit import *

# ───────────────────────── 5-year planning model ───────────────────────
YEARS = ["Y1", "Y2", "Y3", "Y4", "Y5"]
# ── planning driver assumptions (all illustrative) ─────────────────────
DEVICES = [500, 3_000, 10_000, 26_000, 50_000]        # units placed
SUBS = [250, 1_600, 6_400, 17_600, 36_000]            # average paid subscriptions
B2B = [0.075, 0.30, 0.72, 1.55, 2.50]                 # $M operator / pilot revenue
HWR_COGS = [108.0, 96.0, 82.0, 66.0, 58.0]            # $ device cost of goods, falling with scale
SUB_COGS = [0.25, 0.23, 0.22, 0.21, 0.20]             # subscription cost of revenue ratio
B2B_COGS = [0.35, 0.34, 0.33, 0.31, 0.30]             # operator delivery cost ratio
OPEX = [0.70, 1.25, 2.20, 3.60, 5.80]                 # $M operating expense
HEADC = [6, 11, 20, 30, 42]                           # headcount at year end

DEVICE_REV = [d * 149 / 1_000_000 for d in DEVICES]   # $M at a $149 ASP
SUB_REV = [s * 144 / 1_000_000 for s in SUBS]         # $M at $12 / month ($144 ARPU)
REVENUE = [DEVICE_REV[i] + SUB_REV[i] + B2B[i] for i in range(5)]
COGS = [DEVICE_REV[i] * HWR_COGS[i] / 149 + SUB_REV[i] * SUB_COGS[i] + B2B[i] * B2B_COGS[i] for i in range(5)]
GP = [REVENUE[i] - COGS[i] for i in range(5)]
GM = [GP[i] / REVENUE[i] for i in range(5)]
EBITDA = [GP[i] - OPEX[i] for i in range(5)]


def build(b):
    finances(b)
    pnl(b)
    funds(b)
    risks(b)
    closing(b)


def fmt(v, d=2):
    return f"{v:,.{d}f}"


# ────────────────────────── 28 financial plan ──────────────────────────
def finances(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "07 / Financial plan", "Five-year planning model: revenue build",
           "Illustrative base case. Assumptions are planning inputs, not forecasts, guidance or commitments.", num=n)

    # revenue bars
    card(s, ML, 1.74, 7.72, 3.30, fill=SURF)
    tx(s, ML + 0.28, 1.92, 6.0, 0.24, "TOTAL REVENUE BY YEAR — $M", size=8, color=MUTED, bold=True, track=110)
    tx(s, ML + 5.40, 1.92, 2.3, 0.24, "≈ 140 % CAGR", size=8, color=ACCENT, bold=True, align="r", track=60)
    bars(s, ML + 0.44, 2.44, 5.0, 1.90, REVENUE, labels=YEARS,
         colors=[LAV_SOFT, LAV, ACCENT3, PURPLE, ACCENT], maxv=max(REVENUE) * 1.12,
         value_labels=[f"${v:,.2f}M" for v in REVENUE], gap=0.26)
    # stacked composition for the final year
    tx(s, ML + 5.86, 2.36, 1.6, 0.24, "Y5 REVENUE MIX", size=7.5, color=MUTED, bold=True, track=110)
    mix = [("Subscriptions", SUB_REV[4]), ("Devices", DEVICE_REV[4]), ("B2B / operator", B2B[4])]
    my = 2.66
    for i, (t, v) in enumerate(mix):
        col = [ACCENT, LAV, OK][i]
        tx(s, ML + 5.86, my, 1.7, 0.22, t, size=8.5, color=TEXT2)
        tx(s, ML + 5.86, my + 0.20, 1.7, 0.26, f"${v:,.2f}M", size=11, color=INK, bold=True)
        hbar(s, ML + 5.86, my + 0.50, 1.60, 0.10, v / REVENUE[4], color=col)
        tx(s, ML + 5.86, my + 0.62, 1.6, 0.2, f"{v/REVENUE[4]*100:.0f} % of Y5 revenue", size=7, color=MUTED)
        my += 0.86

    # planning inputs
    card(s, ML + 7.98, 1.74, 3.79, 3.30, fill=ACCENT, line=None)
    tx(s, ML + 8.24, 1.92, 3.3, 0.24, "PLANNING INPUTS", size=8, color=LAV, bold=True, track=120)
    inputs = [("Devices placed", "500 → 50,000"), ("Paid subscriptions (avg)", "250 → 36,000"),
              ("Device ASP", "$149"), ("Consumer subscription", "$12 / month"),
              ("Annual ARPU per subscriber", "$144"), ("Operator revenue", "$75k → $2.5M"),
              ("Blended gross margin", "52 % → 68 %")]
    iy = 2.24
    for k, v in inputs:
        tx(s, ML + 8.24, iy, 1.9, 0.24, k, size=8.5, color=LIGHT2, anchor="m")
        tx(s, ML + 10.14, iy, 1.4, 0.24, v, size=9, color=LIGHT, bold=True, align="r", anchor="m")
        hline(s, ML + 8.24, iy + 0.28, 3.3, color=DARK_BORDER, lw=0.5)
        iy += 0.38

    # assumption notes
    card(s, ML, 5.20, CW, 1.60, fill=SURF2)
    tx(s, ML + 0.28, 5.38, 6.0, 0.24, "WHAT HAS TO BE TRUE — AND WHAT IS DELIBERATELY NOT MODELLED",
       size=8, color=MUTED, bold=True, track=110)
    left = ["Hardware cost reaches $52 per unit at 10k volume and yield holds.",
            "Support cost stays under $1.60 per wearer per month as the base grows.",
            "Subscription churn below 2 % per month after the first 90 days."]
    right = ["Not modelled: reimbursement, acquisition of a competitor, hardware margin expansion beyond scale, "
             "or any enterprise contract above $300k.",
             "Excluded: taxes, financing costs, depreciation, working capital, warranty tail and R&D capitalisation."]
    bullets(s, ML + 0.28, 5.68, 5.6, 1.0, left, size=8.5, dot="·", gap=4, line=1.24)
    tx(s, ML + 6.10, 5.68, 5.6, 1.0, right[0], size=8.5, color=TEXT2, line=1.28)
    tx(s, ML + 6.10, 6.22, 5.6, 0.5, right[1], size=8.5, color=TEXT2, line=1.28)
    footer(s, n, right="Financial plan")


# ────────────────────────────── 29 P&L ─────────────────────────────────
def pnl(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "07 / Financial plan", "Profit and loss: break-even in year four",
           "Planning scenario only. Break-even timing is highly sensitive to adoption, support cost and churn.", num=n)

    rows = [["$M, except margin and headcount"] + YEARS,
            ["Device revenue"] + [fmt(v) for v in DEVICE_REV],
            ["Subscription revenue"] + [fmt(v) for v in SUB_REV],
            ["Operator / pilot revenue"] + [fmt(v) for v in B2B],
            ["Total revenue"] + [fmt(v) for v in REVENUE],
            ["Cost of revenue"] + [fmt(-v) for v in COGS],
            ["Gross profit"] + [fmt(v) for v in GP],
            ["Gross margin"] + [f"{v*100:.0f} %" for v in GM],
            ["Operating expense"] + [fmt(-v) for v in OPEX],
            ["EBITDA (planning)"] + [fmt(v) for v in EBITDA]]
    tbl = table(s, ML, 1.66, [3.10, 1.73, 1.73, 1.73, 1.73, 1.75], rows, row_h=0.335, head_h=0.32,
                size=9.5, head_size=8.5, align=["r"] * 6, head_align=["l"] + ["r"] * 5, bold_col0=True,
                row_colors=[None, None, None, None, None, None, None, SURF2, None, LAV_SOFT])
    # emphasise the EBITDA row (last row)
    for c in range(6):
        cell = tbl.cell(9, c)
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.color.rgb = rgb(WARN if c > 0 and EBITDA[c - 1] < 0 else OK)

    # margin trend
    card(s, ML, 5.24, 6.62, 1.56, fill=SURF)
    tx(s, ML + 0.26, 5.40, 6.0, 0.24, "GROSS MARGIN TRAJECTORY — WHY IT IMPROVES", size=8, color=MUTED, bold=True, track=110)
    bars(s, ML + 0.34, 5.72, 5.9, 0.60, GM, maxv=max(GM) * 1.12,
         colors=[LAV_SOFT, LAV, ACCENT3, PURPLE, ACCENT], gap=0.34,
         value_labels=[f"{v*100:.0f} %" for v in GM])
    for i, y in enumerate(YEARS):
        tx(s, ML + 0.34 + i * ((5.9 - 0.34 * 4) / 5 + 0.34), 6.44, 1.0, 0.2, y, size=8, color=MUTED, align="c")

    card(s, ML + 6.88, 5.24, 4.89, 1.56, fill=SURF2)
    tx(s, ML + 7.14, 5.40, 4.3, 0.24, "THE THREE CONDITIONS FOR BREAK-EVEN", size=8, color=MUTED, bold=True, track=110)
    conds = [("Mix shifts to software", "subscription share rises from 24 % to 34 % of revenue"),
             ("Hardware stops losing money", "COGS falls from $90 to $52 per unit"),
             ("Support scales sub-linearly", "automation before headcount")]
    cy = 5.72
    for t, d in conds:
        rich(s, ML + 7.14, cy, 4.3, 0.34, [{"runs": [
            {"t": t + " — ", "size": 9, "bold": True, "color": ACCENT}, {"t": d, "size": 9, "color": TEXT2}], "line": 1.22}])
        cy += 0.36
    footer(s, n, right="Financial plan")


# ─────────────────────────── 30 funding ask ────────────────────────────
def funds(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "07 / Financial plan", "The ask: $1.5M to buy evidence, not features",
           "An 18-month plan to reach a validated, pilot-ready product with measurable endpoints.", num=n)

    card(s, ML, 1.76, 3.60, 2.30, fill=ACCENT, line=None)
    tx(s, ML + 0.26, 1.94, 3.1, 0.24, "RAISE", size=8, color=LAV, bold=True, track=130)
    tx(s, ML + 0.26, 2.18, 3.1, 0.6, "$1.5M", size=40, color=LIGHT, bold=True, line=1.0)
    tx(s, ML + 0.26, 2.84, 3.1, 0.28, "pre-seed", size=11, color=LAV, bold=True, track=60)
    tx(s, ML + 0.26, 3.18, 3.1, 0.7, "≈ 18 months of runway to a validated, pilot-ready milestone.",
       size=9.5, color=LIGHT2, line=1.3)

    # use of funds
    uses = [("Product & hardware verification", 0.35, ACCENT),
            ("Pilot, evidence & safety validation", 0.25, ACCENT3),
            ("Engineering & data platform", 0.20, PURPLE),
            ("Security, privacy & regulatory", 0.10, OK),
            ("Partner GTM & contingency", 0.10, WARN)]
    card(s, ML + 3.80, 1.76, 7.97, 2.30, fill=SURF)
    tx(s, ML + 4.06, 1.94, 7.0, 0.24, "USE OF FUNDS — PLANNING ALLOCATION", size=8, color=MUTED, bold=True, track=110)
    for i, (label, pct, col) in enumerate(uses):
        y = 2.26 + i * 0.34
        progress_row(s, ML + 4.06, y, 7.45, label, f"{pct*100:.0f}%  ${1.5*pct:.2f}M", pct, color=col,
                     size=9, label_w=3.30)

    # milestones
    tx(s, ML, 4.26, 8.0, 0.24, "WHAT THE MONEY BUYS — MILESTONES AT MONTH 18", size=8, color=MUTED, bold=True, track=110)
    miles = [("2–3", "pilot partners signed with written protocols"),
             ("100–150", "target wearers generating continuous data"),
             ("< 5 min", "median time from alert to acknowledgement"),
             ("> 90 %", "target alert precision, adjudicated by clinicians"),
             ("1", "evidence pack suitable for a provider or payer conversation")]
    for i, (v, d) in enumerate(miles):
        x = ML + i * 2.37
        card(s, x, 4.54, 2.22, 1.30, fill=SURF)
        tx(s, x + 0.20, 4.70, 1.9, 0.4, v, size=17, color=ACCENT, bold=True, line=1.03)
        tx(s, x + 0.20, 5.14, 1.9, 0.6, d, size=8.5, color=TEXT2, line=1.24)

    card(s, ML, 6.00, CW, 0.84, fill=SURF2)
    tx(s, ML + 0.26, 6.12, 6.0, 0.22, "USE OF FUNDS IS A HYPOTHESIS TOO", size=8, color=MUTED, bold=True, track=110)
    tx(s, ML + 0.26, 6.38, 11.2, 0.4,
       "Allocation shown is a planning view. Raise size, valuation, instrument and timing require founder and legal "
       "confirmation, and will be revisited after the pilot readout — capital should follow evidence, not precede it.",
       size=8.5, color=TEXT2, line=1.3)
    footer(s, n, right="Financing")


# ────────────────────────────── 31 risks ───────────────────────────────
def risks(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "07 / Financial plan", "Risks named early, with the response already designed",
           "A pilot exists to test failure modes. These are the six that would end the company if unmanaged.", num=n)

    items = [
        ("Measurement bias and noise", "Prototype sensors drift with skin, motion and temperature.",
         "Bench validation against reference instruments; per-signal quality gates; subgroup review.", 3),
        ("False alerts erode trust", "One bad night-time alert can end a family's willingness to continue.",
         "Shadow mode before alerting; clinician adjudication; tuning loop with a published false-alert target.", 3),
        ("Battery and wear abandonment", "A band that is not worn cannot save anyone.",
         "Daily wear-time telemetry; usability interviews; charger and enclosure redesign in Horizon 2.", 2),
        ("Emergency delivery failure", "A missed escalation is the most serious failure mode in the product.",
         "Delivery receipts, retry ladder, fallback contacts, explicit non-emergency disclaimers, human confirmation.", 3),
        ("Privacy and health-data exposure", "Health data attracts both regulation and attackers.",
         "Least privilege, credential rotation, retention limits, threat model and audit logging before pilot start.", 3),
        ("Regulatory scope drift", "A wellness product can drift into a medical device claim by accident.",
         "Define intended use; no diagnostic language; clinical and legal review before each pilot.", 2),
    ]
    for i, (t, d, resp, sev) in enumerate(items):
        x = gx((i % 2) * 6)
        y = 1.76 + (i // 2) * 1.44
        w = gw(6, 0.22)
        card(s, x, y, w, 1.32, fill=SURF)
        tx(s, x + 0.24, y + 0.16, 4.2, 0.24, t, size=11, color=INK, bold=True)
        for k in range(3):
            dot(s, x + w - 1.16 + k * 0.16, y + 0.22, 0.10, ACCENT if k < sev else SURF3)
        tx(s, x + 0.24, y + 0.44, w - 0.48, 0.34, d, size=8.5, color=TEXT2, line=1.24)
        hline(s, x + 0.24, y + 0.84, w - 0.48, color=BORDER, lw=0.5)
        rich(s, x + 0.24, y + 0.92, w - 0.48, 0.36, [{"runs": [
            {"t": "Response: ", "size": 8.5, "bold": True, "color": ACCENT}, {"t": resp, "size": 8.5, "color": TEXT2}], "line": 1.24}])

    card(s, ML, 6.10, CW, 0.80, fill=ACCENT, line=None)
    tx(s, ML + 0.28, 6.22, 11.2, 0.24, "PRODUCT GUARDRAIL — NON-NEGOTIABLE", size=8, color=LAV, bold=True, track=120)
    tx(s, ML + 0.28, 6.48, 11.2, 0.32,
       "NeuroLink Wear supports wellness and safety decisions made by humans. It is not a diagnostic device, "
       "does not replace emergency services, and never presents a single sensor reading as a clinical conclusion.",
       size=9, color=LIGHT, line=1.28)
    footer(s, n, right="Risks")


# ─────────────────────────── 32 close / next step ──────────────────────
def closing(b):
    s = slide(b.prs, DARK)
    n = b.num()
    rect(s, 0, 0, W, H, fill=DARK, radius=False)
    rect(s, 0, 0, 0.10, H, fill=ACCENT3, radius=False)
    rect(s, W - 6.1, 0, 6.1, H, fill=DARK2, radius=False)

    tx(s, ML + 0.30, 1.10, 6.4, 0.3, "NEXT STEP", size=9.5, color=LAV, bold=True, track=200)
    tx(s, ML + 0.26, 1.48, 6.5, 1.6, "Make the signal useful\nto someone.", size=34, color=LIGHT, bold=True, line=1.06)
    tx(s, ML + 0.30, 3.06, 6.1, 0.9,
       "Wearable context. Explainable alerts. A safer path to human response — and the evidence to prove it "
       "before we ask anyone to trust it.", size=12, color=LIGHT2, line=1.36)

    asks = [("Pilot partners", "Home-care or senior-living operators willing to run 100–150 wearers with written endpoints."),
            ("Clinical validation support", "Advisors to pre-register endpoints and adjudicate alerts during the pilot."),
            ("Investors", "$1.5M pre-seed aligned with a pilot-led, evidence-first plan.")]
    ty = 3.98
    for t, d in asks:
        tx(s, ML + 0.30, ty, 2.0, 0.24, t.upper(), size=8, color=LAV, bold=True, track=110)
        tx(s, ML + 0.30, ty + 0.26, 5.9, 0.5, d, size=9.5, color=LIGHT2, line=1.28)
        ty += 0.86

    # right panel — the ask recap
    px = W - 5.6
    tx(s, px, 1.10, 4.6, 0.3, "THE PLAN IN ONE COLUMN", size=9, color=DARK_MUTED, bold=True, track=160)
    recap = [("Today", "Working prototype: live telemetry, two-tier detection, caregiver workflow, green test suites."),
             ("Next 6 months", "Hardware verification, delivery integrations, pilot onboarding with 2–3 partners."),
             ("Next 18 months", "100–150 wearers instrumented, precision and response-time evidence, paid renewals."),
             ("Then", "Operator contracts, remote-care partnerships, platform expansion on proven detection quality.")]
    ry = 1.60
    for i, (t, d) in enumerate(recap):
        col = [OK, ACCENT3, LAV, LIGHT][i]
        dot(s, px, ry + 0.05, 0.11, col)
        if i < 3:
            vline(s, px + 0.05, ry + 0.20, 1.06, color=DARK_BORDER, lw=0.75)
        tx(s, px + 0.34, ry, 4.2, 0.24, t, size=10, color=col, bold=True, track=30)
        tx(s, px + 0.34, ry + 0.28, 4.2, 0.7, d, size=9, color=LIGHT2, line=1.3)
        ry += 1.26

    card(s, px, 6.02, 4.6, 0.86, fill=DARK3, line=DARK_BORDER)
    tx(s, px + 0.22, 6.12, 4.2, 0.2, "CONTACT — EDIT BEFORE SENDING", size=7.5, color=DARK_MUTED, bold=True, track=120)
    tx(s, px + 0.22, 6.34, 4.2, 0.26, "founders@neurolinkwear.example  ·  +00 000 000 000", size=9, color=LIGHT)
    tx(s, px + 0.22, 6.60, 4.2, 0.22, "Replace with the real contact details.", size=7.5, color=DARK_MUTED)
    footer(s, n, "NEUROLINK WEAR", right="THANK YOU", dark=True)

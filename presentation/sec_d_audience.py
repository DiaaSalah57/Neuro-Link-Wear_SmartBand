"""Deck section D — target audience, personas, jobs-to-be-done and adoption journey."""
from pptx.enum.shapes import MSO_SHAPE

from kit import *


def build(b):
    audience(b)
    personas(b)
    jobs(b)


# ────────────────────────── 16 target audience ─────────────────────────
def audience(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "04 / Audience", "Who we build for, in order",
           "One wearer, one payer, one operator. Every segment is defined by a concrete job — not by a demographic.",
           num=n)

    tiers = [
        ("PRIMARY", "Older adults aging at home", "WEARER — NOT THE BUYER",
         "65+, living alone or with a partner, managing hypertension, COPD, diabetes or frailty.",
         ["Wants to stay independent and not be “watched”",
          "Will not tolerate charging a device daily",
          "Needs the device to be invisible under a sleeve"],
         "Success metric: 20+ wear-hours per day, 90 % of days, after month one.", ACCENT),
        ("PRIMARY", "Family caregivers", "BUYER + DAILY USER",
         "Adult children aged 40–60 and spouses who already act as the informal safety net from a distance.",
         ["Already anxious between calls and visits",
          "Pays for peace of mind, not for a gadget",
          "Needs an answer in seconds during a scare"],
         "Success metric: alert acknowledged in under 5 minutes; subscription retained at 6 months.", ACCENT3),
        ("SECONDARY", "Home care & senior living", "ENTERPRISE BUYER",
         "Home-care agencies, assisted-living operators and care cooperatives running staffed caseloads.",
         ["Needs multi-wearer oversight and an audit trail",
          "Buys workflows, not dashboards",
          "Exits trials that create extra staff work"],
         "Success metric: staff minutes saved per alert; pilot converts to paid renewal.", PURPLE),
        ("TERTIARY", "Remote care ecosystem", "FUTURE PARTNER",
         "Remote-monitoring providers, payers and employers exploring supported self-management.",
         ["Requires evidence of detection quality first",
          "Asks about data governance, retention and consent",
          "Moves slowly, contracts in multiples"],
         "Success metric: validated evidence pack and a signed integration pilot.", OK),
    ]
    cw = gw(6, 0.18)
    for i, (tier, title, role, who, bullets_, metric, col) in enumerate(tiers):
        x = gx((i % 2) * 6)
        y = 1.76 + (i // 2) * 2.42
        card(s, x, y, cw, 2.28, fill=SURF)
        rect(s, x, y, 0.045, 2.28, fill=col, radius=True, adj=0.5)
        tx(s, x + 0.26, y + 0.18, 1.2, 0.2, tier, size=7.5, color=col, bold=True, track=130)
        tx(s, x + 1.30, y + 0.18, 2.6, 0.2, role, size=7.5, color=MUTED, bold=True, track=90)
        tx(s, x + 0.26, y + 0.44, cw - 0.5, 0.28, title, size=14, color=INK, bold=True)
        tx(s, x + 0.26, y + 0.76, cw - 0.5, 0.42, who, size=9, color=TEXT2, line=1.26)
        bullets(s, x + 0.26, y + 1.22, cw - 0.5, 0.8, bullets_, size=8.5, dot="·", gap=3, line=1.22, dot_color=col)
        hline(s, x + 0.26, y + 1.94, cw - 0.52, color=BORDER, lw=0.5)
        tx(s, x + 0.26, y + 2.02, cw - 0.5, 0.24, metric, size=8, color=col, line=1.2)
    footer(s, n, right="Audience")


# ────────────────────────────── 17 personas ────────────────────────────
def personas(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "04 / Audience", "Three people decide whether this works",
           "Adoption fails on the wearer's wrist, not in the demo. Design for all three at once.", num=n)

    people = [
        ("MT", "Margaret, 78", "The wearer", "Hypertension and mild COPD · lives alone · two falls in 18 months",
         "“I don't want to be a patient in my own house.”",
         ["Wants to keep living at home without a nurse in the room",
          "Hates being reminded that she is old",
          "Will abandon anything that itches, buzzes or needs charging"],
         ["Wrist-worn, unnoticeable, multi-day battery",
          "Alerts she can dismiss when she is fine",
          "No cameras, no constant calling"], ACCENT),
        ("SR", "Sarah, 46", "The family caregiver", "Lives 90 minutes away · works full time · primary contact",
         "“If something happens at 2 a.m., I need to know before the morning call.”",
         ["Guilt about not being there",
          "Already drowning in group chats and check-in calls",
          "Cannot interpret a raw vitals chart"],
         ["One screen with her mother's real state",
          "Plain-language explanation and a next step",
          "One-tap escalation with location"], ACCENT3),
        ("DO", "Dana, 39", "The care manager", "Runs 60 home-care clients · 14 field staff",
         "“I need fewer surprises and an audit trail I can hand to a regulator.”",
         ["Accountable for outcomes she cannot see",
          "Field staff resist extra data entry",
          "Must justify every subscription line"],
         ["Caseload-level triage and trend reporting",
          "Evidence trail per incident",
          "Deployment that does not add work"], PURPLE),
    ]
    for i, (init, name, role, context, quote, pains, gains, col) in enumerate(people):
        marks = 3 if i == 0 else (2 if i == 1 else 3)
        x = gx(i * 4)
        w = gw(4, 0.24)
        card(s, x, 1.76, w, 4.98, fill=SURF)
        rect(s, x, 1.76, w, 0.05, fill=col, radius=True, adj=0.5)
        oval(s, x + 0.26, 2.02, 0.64, 0.64, LAV_SOFT)
        tx(s, x + 0.26, 2.16, 0.64, 0.36, init, size=15, color=col, bold=True, align="c")
        tx(s, x + 1.02, 2.04, w - 1.2, 0.28, name, size=14, color=INK, bold=True)
        tx(s, x + 1.02, 2.32, w - 1.2, 0.22, role, size=9, color=col, bold=True, track=40)
        tx(s, x + 1.02, 2.53, 1.0, 0.2, "TECH COMFORT", size=6.5, color=MUTED, track=60)
        for k in range(3):
            dot(s, x + 1.86 + k * 0.14, 2.57, 0.09, col if k < marks else SURF3)
        tx(s, x + 0.26, 2.78, w - 0.52, 0.42, context, size=8.5, color=MUTED, line=1.25)
        rect(s, x + 0.26, 3.26, w - 0.52, 0.62, fill=SURF2, radius=True, adj=0.14)
        tx(s, x + 0.40, 3.34, w - 0.80, 0.48, quote, size=9, color=INK, italic=True, line=1.24)
        tx(s, x + 0.26, 4.02, w - 0.52, 0.22, "PAINS", size=7.5, color=MUTED, bold=True, track=110)
        bullets(s, x + 0.26, 4.26, w - 0.52, 1.0, pains, size=8.5, dot="·", gap=4, line=1.22, dot_color=DANGER)
        tx(s, x + 0.26, 5.36, w - 0.52, 0.22, "WHAT EARNS THEIR TRUST", size=7.5, color=MUTED, bold=True, track=110)
        bullets(s, x + 0.26, 5.60, w - 0.52, 1.0, gains, size=8.5, dot="·", gap=4, line=1.22, dot_color=col)
    footer(s, n, right="Audience")


# ─────────────────────── 18 jobs-to-be-done & journey ──────────────────
def jobs(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "04 / Audience", "What each person hires the product to do",
           "Jobs-to-be-done mapped to the feature that answers it today — and to the metric that proves it worked.",
           num=n)

    rows = [["Stakeholder", "Job to be done", "Feature serving it today", "Proof metric"],
            ["Wearer", "“Let me keep living alone without feeling supervised.”", "Unobtrusive band, dismissible alerts, no cameras or microphones", "Wear-days per month"],
            ["Wearer", "“Tell me when something is actually wrong.”", "Two-tier detection with wearer-facing status and vibration cues", "Alert acknowledgement rate"],
            ["Family caregiver", "“Show me she is fine without me calling again.”", "Live Overview with vitals, motion state and 24 h trend sparklines", "Sessions per week"],
            ["Family caregiver", "“When it goes wrong, tell me what to do.”", "Plain-language explanation, recommendation list, one-tap dispatch", "Time to acknowledgement"],
            ["Family caregiver", "“Keep the record I will need later.”", "Incident timeline with GPS, dispatch log, downloadable history", "Incidents with complete logs"],
            ["Care manager", "“Triage 60 clients without 60 phone calls.”", "Caseload-ready alert queue, severity sorting, per-wearer thresholds", "Alerts resolved per staff hour"],
            ["Care manager", "“Defend the decision if something goes wrong.”", "Immutable clinical floors plus audit trail on every configuration change", "Audit completeness"],
            ["Clinician (reviewer)", "“Understand why an alert fired before I act.”", "Evidence panel: z-scores, core-equivalent temperature, hypoxic burden", "Clinician agreement rate"]]
    table(s, ML, 1.72, [1.62, 3.50, 4.49, 1.86], rows, row_h=0.42, head_h=0.32,
          size=8.5, head_size=7.5, bold_col0=True, align=["l", "l", "l", "l"])

    # adoption journey
    tx(s, ML, 5.50, 6.0, 0.24, "THE ADOPTION JOURNEY — WHERE MOST WEARABLES FAIL",
       size=8, color=MUTED, bold=True, track=110)
    stages = [("Day 0", "Fit & first sync", "Band paired, MQTT verified", OK),
              ("Day 1–3", "Warming up", "Baselines form, confidence climbs", ACCENT3),
              ("Week 1", "First real alert", "Explained, acknowledged, resolved", WARN),
              ("Week 2–4", "Trust or churn", "False-alert rate decides retention", DANGER),
              ("Month 2+", "Routine", "Baselines sharpen, dependency forms", ACCENT)]
    jx = ML
    for i, (when, title, sub, col) in enumerate(stages):
        w = gw(2.4, 0.14)
        card(s, jx, 5.78, w, 1.06, fill=SURF)
        rect(s, jx, 5.78, w, 0.045, fill=col, radius=True, adj=0.5)
        tx(s, jx + 0.16, 5.90, w - 0.3, 0.2, when, size=7.5, color=col, bold=True, track=60)
        tx(s, jx + 0.16, 6.10, w - 0.3, 0.22, title, size=10, color=INK, bold=True)
        tx(s, jx + 0.16, 6.32, w - 0.3, 0.44, sub, size=8, color=TEXT2, line=1.22)
        if i < len(stages) - 1:
            tx(s, jx + w, 6.12, 0.14, 0.24, "›", size=11, color=BORDER_STRONG, align="c", bold=True)
        jx += w + 0.14
    footer(s, n, right="Audience")

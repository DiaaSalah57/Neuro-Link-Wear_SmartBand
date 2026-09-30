"""
NeuroLink Wear — investor & technical pitch deck builder.

Run:  python3 presentation/build.py
Out:  NeuroLink_Wear_Investor_Deck.pptx  (repo root)

Design: minimalist, built from the dashboard design tokens (static/css/styles.css).
Everything is native PowerPoint — shapes, text boxes and tables — so the file stays
fully editable. Speaker notes are attached to every slide.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pptx import Presentation

import kit
import sec_a1_open
import sec_a2_problem_market
import sec_b_product
import sec_c_intel
import sec_c2_verify
import sec_d_audience
import sec_e_roadmap
import sec_f_business
import sec_g_fin

OUT = Path(__file__).resolve().parents[1] / "NeuroLink_Wear_Investor_Deck.pptx"


class Builder:
    def __init__(self, prs):
        self.prs = prs
        self.n = 0

    def num(self):
        self.n += 1
        return self.n

    def divider(self, section, title, subtitle, items=None, label=None):
        self.n += 1
        return kit.divider(self.prs, self.n, section, title, subtitle, items, label)


NOTES = {
    1: "Open with the loop, not the technology: sense → understand → respond. This deck is written so a technical "
       "reviewer and an investor can both follow it; every claim carries its status.",
    2: "Set expectations: nine sections, each readable on its own. The ✔ / ◦ legend matters — it separates what is "
       "running today from what is a roadmap hypothesis.",
    3: "One slide to anchor the conversation: a working prototype exists, the intelligence layer is explainable, and "
       "the ask funds evidence rather than more features.",
    4: "Section 01 — the problem is not measurement, it is context and response.",
    5: "Walk the day timeline slowly. The night-time fall with no alert is the emotional centre of the pitch.",
    6: "Be disciplined on market size: name the beachhead, then show that the same platform reaches operators. The "
       "scale illustration is arithmetic, not a TAM claim.",
    7: "The timing argument: demographics, normalised wrist behaviour, and a gap that consumer devices deliberately "
       "do not fill.",
    8: "Section 02 — the product: device, intelligence and care workflow sharing one data spine.",
    9: "Explain the loop closing: alerts feed baselines, so the system gets sharper for that specific wearer.",
    10: "This is a wireframe of the shipped dashboard, not a screenshot. Demo the live app after this slide.",
    11: "Be explicit: prototype-grade hardware. The sensor list is real, the accuracy work is a pilot gate.",
    12: "Architecture answer for the technical judge: one ingest path serves both simulated payloads and real "
        "devices.",
    13: "Section 03 — intelligence. This is the differentiator: equations plus calibration instead of a black box.",
    14: "Stress the two commercial consequences: coverage on day one for a new wearer, and alerts that can be "
        "explained to a clinician.",
    15: "The guided reference example is the clearest illustration of personalisation — a nurse's oral thermometer "
        "becomes the wearer's own calibration offset.",
    16: "Detection breadth matters for triage, but repeat the guardrail: this supports decisions, it does not "
        "diagnose.",
    17: "Emphasise the asymmetry: personalisation can only add sensitivity. Clinical floors are immutable.",
    18: "The language layer is optional by design — detection must never depend on an external model being "
        "available.",
    19: "Use this slide for diligence questions: three suites, all green, every fixed bug closed with a regression "
        "test.",
    20: "Section 04 — audience. One wearer, one payer, one operator.",
    21: "Segments in priority order: beachhead first, enterprise second, ecosystem later.",
    22: "Adoption fails on the wrist. If Margaret will not wear it, Sarah's dashboard is irrelevant.",
    23: "Jobs-to-be-done mapped to shipped features and to the metric that proves each one worked.",
    24: "Section 05 — roadmap. Nothing advances a horizon until the gate before it is passed.",
    25: "Keep the three horizons visually separate; the honest framing is ‘shipped / next / later’.",
    26: "Wearer-side features. Each card states the gate that would justify building it.",
    27: "Caregiver-side features. Flag that delivery integrations are partner and regulatory dependencies, not just "
        "engineering work.",
    28: "Platform bets. The standing rules at the bottom are the guardrails no roadmap item can move.",
    29: "Section 06 — business model. Hardware opens the account, software keeps it.",
    30: "Four revenue streams; the subscription is the engine, the device is the entry point.",
    31: "Unit economics are illustrative. The four metrics at the bottom are the ones that decide the business.",
    32: "Go-to-market: buy proof before reach. Show the pilot scorecard — this is what the money measures.",
    33: "The pilot is an instrument. Pre-registered endpoints and shadow mode are what make the result credible.",
    34: "Section 07 — financial plan. Repeat the caveat on every financial slide: planning scenario, not a "
        "forecast.",
    35: "Revenue build from $0.19M to $15.13M with the driver assumptions visible in one column.",
    36: "Break-even in year four, and name the three conditions that have to hold for it.",
    37: "The ask: $1.5M buys evidence. Use of funds is a hypothesis too — revisit it after the pilot readout.",
    38: "Risks are named early with the response already designed. Close on the guardrail statement.",
    39: "Close: make the signal useful to someone. Ask for pilot partners, clinical validation support and aligned "
        "capital. Replace the placeholder contact block before sending.",
}


def build():
    prs = Presentation()
    prs.slide_width = kit.Inches(kit.W)
    prs.slide_height = kit.Inches(kit.H)
    b = Builder(prs)

    # ── opening
    sec_a1_open.build(b)

    # ── 01 problem & market
    b.divider("01", "The gap between check-ins",
              "Continuous context and a response path — the problem worth solving first.",
              ["Signals without context", "Trends that start quietly", "Responses that are improvised"],
              label="Problem & market")
    sec_a2_problem_market.build(b)

    # ── 02 solution & product
    b.divider("02", "Device, intelligence, action",
              "One sensing platform: a wearable band, an explainable AI engine and a caregiver workflow.",
              ["Five sensors on an ESP32", "Two-tier detection", "Six caregiver views shipped"],
              label="Solution & product")
    sec_b_product.build(b)

    # ── 03 intelligence
    b.divider("03", "Explainable intelligence",
              "Equations and per-wearer calibration instead of an opaque model.",
              ["No training dataset required", "Clinical floors that never move", "Every alert cites its evidence"],
              label="Intelligence")
    sec_c_intel.build(b)
    sec_c2_verify.build(b)

    # ── 04 audience
    b.divider("04", "Who we build for",
              "One wearer, one payer, one operator — each with a concrete job to be done.",
              ["Older adults at home", "Family caregivers", "Home-care and senior-living operators"],
              label="Target audience")
    sec_d_audience.build(b)

    # ── 05 roadmap
    b.divider("05", "Roadmap & future features",
              "What is shipped, what pilots next, and what the platform unlocks after that.",
              ["Shipped today — the working build", "Next 0–12 months — pilot gates",
               "Later 12–36 months — platform bets"],
              label="Roadmap")
    sec_e_roadmap.build(b)

    # ── 06 business
    b.divider("06", "Business model",
              "Hardware opens the account; subscriptions and operator contracts fund the company.",
              ["Device sale at $149 ASP", "Subscription at $12 / month", "Operator licence per wearer"],
              label="Business & economics")
    sec_f_business.build(b)

    # ── 07 financial plan
    b.divider("07", "Financial plan & the ask",
              "An illustrative five-year plan and a $1.5M pre-seed to buy evidence, not features.",
              ["Break-even planned in year four", "$1.5M for ~18 months", "Milestone: validated, pilot-ready"],
              label="Financials & financing")
    sec_g_fin.build(b)

    # ── speaker notes
    for i, slide in enumerate(prs.slides, start=1):
        text = NOTES.get(i)
        if text:
            slide.notes_slide.notes_text_frame.text = text

    prs.save(OUT)
    print(f"saved {OUT}  ({len(prs.slides)} slides)")
    return OUT


if __name__ == "__main__":
    build()

"""Deck section C-extension — verification & QA evidence."""
from kit import *


def build(b):
    verification(b)


# ──────────────────────── verification & quality ───────────────────────
def verification(b):
    s = slide(b.prs)
    n = b.num()
    header(s, "03 / Intelligence", "Verified, not asserted: the evidence in the repository",
           "Three independent suites run against the live server — all green, all re-runnable on demand.", num=n)

    suites = [("141", "QA battery checks", "51 UI · 1 session · 55 backend · 1 WebSocket · 8 sign-in · 25 end-to-end",
               "PASS", OK, OK_BG),
              ("74", "Calibration-suite checks", "Equations, calibration module, two-tier OR-gates, HTTP API, demo triggers",
               "PASS ×2 · idempotent", OK, OK_BG),
              ("17", "DOM interaction checks", "Sign-in regression, Calibration tab panels, auto-fit, guided reference, sliders",
               "PASS", OK, OK_BG),
              ("6", "Bugs found and fixed", "Each one reproduced, root-caused and re-verified by a regression test",
               "CLOSED", ACCENT, LAV_SOFT)]
    for i, (v, t, d, status, col, bgc) in enumerate(suites):
        x = gx(i * 3)
        w = gw(3, 0.22)
        card(s, x, 1.76, w, 1.86, fill=SURF)
        rect(s, x, 1.76, w, 0.05, fill=col, radius=True, adj=0.5)
        tx(s, x + 0.22, 1.94, w - 0.44, 0.44, v, size=26, color=col, bold=True, line=1.0)
        tx(s, x + 0.22, 2.42, w - 0.44, 0.24, t, size=10.5, color=INK, bold=True)
        tx(s, x + 0.22, 2.70, w - 0.44, 0.62, d, size=8, color=TEXT2, line=1.26)
        chip(s, x + 0.22, 3.26, min(w - 0.44, 1.85), 0.26, status, fg=col, bgc=bgc, size=7.5, track=30, align="c")

    # bugs table — what was wrong and why it matters
    rows = [["Defect found by the suites", "Why it mattered", "Resolution"],
            ["Confirm dialogs always cancelled", "Every delete / resolve confirmation silently did nothing",
             "Decision flag added to the modal resolver"],
            ["Buttons disabled after save", "A save could leave the UI permanently locked",
             "Element captured before the await"],
            ["View / WebSocket lifecycle race", "Slow renders wrote into dead DOM after navigation",
             "Serialised navigation with null-guarded loaders"],
            ["Demo stress scenario could not fire", "The flagship demo alert never appeared",
             "Scenario recalibrated; forced phases snap within one tick"],
            ["Wrong password showed “session expired”", "A simple credential error looked like a security problem",
             "Login 401 now surfaces the real message"],
            ["Demo drills swallowed by cooldown", "Emergency drills silently suppressed for 10 minutes",
             "Drill triggers clear the duplicate-suppression window"]]
    table(s, ML, 3.80, [3.40, 4.66, 3.71], rows, row_h=0.33, head_h=0.30,
          size=8.5, head_size=7.5, bold_col0=True, align=["l", "l", "l"])

    card(s, ML, 6.20, CW, 0.62, fill=SURF2)
    tx(s, ML + 0.26, 6.36, 11.2, 0.3,
       "Reproduce in one command:  python3 calib_suite.py  against a running server — the suite is idempotent and "
       "safe to run repeatedly, which is what a diligence reviewer will ask for.",
       size=8.5, color=TEXT2)
    footer(s, n, right="Verification")

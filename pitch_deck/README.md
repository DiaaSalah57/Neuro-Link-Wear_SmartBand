# NeuroLink Wear — investor pitch deck

| File | What it is |
|---|---|
| `NeuroLink_Wear_Pitch_Deck.pptx` | The generated deck — 22 slides, 16:9, speaker notes embedded on every slide |
| `build_deck.py` | The runnable `python-pptx` script that builds the presentation |
| `SLIDE_SPECS_AND_NOTES.md` | Slide-by-slide visual layout specs and speaker notes, generated from the same source |
| `preview_deck.py` | Optional renderer for PNG/PDF review and text-overflow checks |
| `assets/` | Product and lifestyle images used by the deck |

## Rebuild

```bash
pip install python-pptx pymupdf pillow
python build_deck.py
python preview_deck.py NeuroLink_Wear_Pitch_Deck.pptx --out preview --dpi 110
```

## Customise

- **Facts and numbers:** `FACTS` near the top of `build_deck.py`.
- **Colours and fonts:** design tokens near the top of the script.
- **Team, funding and contact details:** bracketed placeholders on the final slides.
- **Images:** replace files in `assets/` while keeping their filenames.
- **Slides:** edit/add a `slide_*` function and list it in `SLIDES`.

## Storyline (22 slides)

1 Cover · 2 Problem · 3 Solution · 4 Hardware · 5 System architecture · 6 Edge intelligence · 7 Intelligence engine ·
8 AI architecture: sensor to alert · 9 Model roles · 10 Model results · 11 Equation library · 12 Personal calibration ·
13 Detection tiers · 14 Safety workflow · 15 Caregiver experience · 16 Traction · 17 Market · 18 Business model ·
19 Competitive positioning · 20 Roadmap · 21 Team · 22 The ask

**Technical-status note:** slides 8, 11–13 label calibration, equation logic, and independent OR-tier detection as design/validation work where the current repository does not yet implement the full described behavior. The model-results slide labels metrics as offline and non-clinical; reproduce the reported split before external use.

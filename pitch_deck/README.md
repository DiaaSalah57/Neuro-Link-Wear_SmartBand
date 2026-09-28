# NeuroLink Wear — investor pitch deck

| File | What it is |
|---|---|
| `NeuroLink_Wear_Pitch_Deck.pptx` | The generated deck — 16 slides, 16:9, speaker notes embedded on every slide |
| `build_deck.py` | The python-pptx script that builds it (design tokens → helpers → one function per slide) |
| `SLIDE_SPECS_AND_NOTES.md` | Slide-by-slide visual layout specs + speaker notes (generated from the same source) |
| `preview_deck.py` | Optional: renders any python-pptx deck to PNG/PDF without PowerPoint and flags text overflow |
| `assets/` | Hero render, exploded view and two lifestyle photos used by the deck (AI-generated, replace freely) |

## Rebuild

```bash
pip install python-pptx
python build_deck.py                      # writes the .pptx and the specs markdown
python preview_deck.py NeuroLink_Wear_Pitch_Deck.pptx   # optional QA render (needs pymupdf + pillow)
```

## Customise

* **Facts & numbers** — `FACTS` dict at the top of `build_deck.py`; sources are quoted in the speaker notes.
* **Colours / fonts** — tokens at the top of the script (`NAVY`, `VIOLET`, `CYAN`, …, `FONT_HEAD`, `FONT_BODY`).
* **Team, contact, funding ask** — bracketed `[placeholders]` on slides 15–16.
* **Images** — drop your own photos into `assets/` with the same file names; every image is cropped
  to fill its frame automatically (`focus=` shifts the crop). Missing images fall back to a branded gradient.
* **Order / new slides** — add a `slide_*` function and list it in `SLIDES`.

## Storyline (16 slides)

1 Cover · 2 Problem · 3 Solution · 4 Hardware · 5 Architecture · 6 Edge intelligence · 7 AI engine ·
8 Safety workflow · 9 Caregiver experience · 10 Traction · 11 Market · 12 Business model ·
13 Competitive positioning · 14 Roadmap · 15 Team · 16 The ask

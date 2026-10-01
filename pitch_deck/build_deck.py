#!/usr/bin/env python3
"""
NeuroLink Wear — investor pitch deck generator
==============================================

Builds `NeuroLink_Wear_Pitch_Deck.pptx` (22 slides, 16:9) with python-pptx,
embeds speaker notes in every slide, and writes `SLIDE_SPECS_AND_NOTES.md`
(slide-by-slide layout specs + the same notes) next to it.

    pip install python-pptx
    python build_deck.py                # -> NeuroLink_Wear_Pitch_Deck.pptx + SLIDE_SPECS_AND_NOTES.md
    python build_deck.py --out my.pptx  # custom output name

Optional imagery is read from ./assets (hero_band.jpg, exploded_band.jpg,
elder_home.jpg, caregiver_app.jpg). If a file is missing the script draws a
branded gradient placeholder instead, so the script always runs.

Everything is drawn with native shapes/text (no template dependency), so the
deck stays fully editable in PowerPoint / Keynote / Google Slides.
"""
from __future__ import annotations

import argparse
import os
import struct
from dataclasses import dataclass, field

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

# ──────────────────────────────────────────────────────────────────────────────
# 1. DESIGN TOKENS
# ──────────────────────────────────────────────────────────────────────────────
SLIDE_W, SLIDE_H = 13.333, 7.5          # inches (16:9)
MARGIN = 0.6

NAVY = "0F0E2A"      # dark background
NAVY_2 = "1B1A3F"    # cards on dark
NAVY_3 = "262552"    # borders / dividers on dark
VIOLET = "6C3CE9"    # primary
VIOLET_DK = "4B22C9"
INDIGO = "3B5BFF"
CYAN = "22D3EE"      # accent
MINT = "34D399"      # success
AMBER = "F5B301"     # warning
PINK = "F43F7A"      # danger / emergency
LIGHT = "F5F5FA"     # light background
LIGHT_2 = "FFFFFF"   # cards on light
LIGHT_3 = "E6E6F0"   # borders on light
INK = "17172F"       # text on light
SLATE = "5B5B7A"     # muted text on light
MUTED_D = "A9A9C7"   # muted text on dark
WHITE = "FFFFFF"

FONT_HEAD = "Calibri"   # swap for "Montserrat" / "Segoe UI" if installed everywhere you present
FONT_BODY = "Calibri"

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
IMG = {
    "hero": os.path.join(ASSETS, "hero_band.jpg"),
    "exploded": os.path.join(ASSETS, "exploded_band.jpg"),
    "elder": os.path.join(ASSETS, "elder_home.jpg"),
    "caregiver": os.path.join(ASSETS, "caregiver_app.jpg"),
}

# Facts used on slides (keep the sources in the notes up to date if you change them)
FACTS = {
    "who_deaths": "684 000",
    "who_lmic": "80%+",
    "who_medical": "37.3 M",
    "eg_60plus": "9.3 M",
    "eg_60plus_pct": "8.8%",
    "dataset_rows": "1,875",
    "checks": "87",
}


# ──────────────────────────────────────────────────────────────────────────────
# 2. LOW-LEVEL HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_)


def _no_shadow(shape):
    shape.shadow.inherit = False


def rect(slide, x, y, w, h, fill=None, line=None, line_w=0.75, radius=None, alpha=None):
    """Rectangle / rounded rectangle. radius is in inches (absolute)."""
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        s.adjustments[0] = max(0.0, min(0.5, radius / max(0.01, min(w, h))))
    _style(s, fill, line, line_w, alpha)
    return s


def oval(slide, x, y, w, h, fill=None, line=None, line_w=0.75, alpha=None):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(w), Inches(h))
    _style(s, fill, line, line_w, alpha)
    return s


def arrow_right(slide, x, y, w, h, fill=VIOLET):
    s = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    _style(s, fill, None, 0, None)
    return s


def _style(s, fill, line, line_w, alpha):
    _no_shadow(s)
    if fill:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(fill)
        if alpha is not None:
            set_fill_alpha(s, alpha)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(line_w)
    else:
        s.line.fill.background()
    # never let autoshape text show
    s.text_frame.text = ""


def set_fill_alpha(shape, alpha: float):
    """alpha 0..1 on a solid fill (python-pptx has no API for this)."""
    solid = shape._element.spPr.find(qn("a:solidFill"))
    if solid is None:
        return
    clr = solid[0]
    for old in clr.findall(qn("a:alpha")):
        clr.remove(old)
    a = etree.SubElement(clr, qn("a:alpha"))
    a.set("val", str(int(alpha * 100000)))


def gradient(shape, stops, angle=0.0):
    """Linear gradient. stops = [(pos 0..1, 'RRGGBB', alpha 0..1), ...]; angle in degrees (0 = left→right, 90 = top→bottom)."""
    spPr = shape._element.spPr
    for tag in ("a:solidFill", "a:gradFill", "a:noFill", "a:pattFill", "a:blipFill"):
        for el in spPr.findall(qn(tag)):
            spPr.remove(el)
    grad = etree.Element(qn("a:gradFill"))
    grad.set("rotWithShape", "1")
    gs_lst = etree.SubElement(grad, qn("a:gsLst"))
    for pos, hex_, alpha in stops:
        gs = etree.SubElement(gs_lst, qn("a:gs"))
        gs.set("pos", str(int(pos * 100000)))
        c = etree.SubElement(gs, qn("a:srgbClr"))
        c.set("val", hex_)
        if alpha < 1.0:
            a = etree.SubElement(c, qn("a:alpha"))
            a.set("val", str(int(alpha * 100000)))
    lin = etree.SubElement(grad, qn("a:lin"))
    lin.set("ang", str(int(angle * 60000)))
    lin.set("scaled", "0")
    geom = spPr.find(qn("a:prstGeom"))
    if geom is None:
        geom = spPr.find(qn("a:custGeom"))
    geom.addnext(grad)


def grad_rect(slide, x, y, w, h, stops, angle=0.0, radius=None):
    s = rect(slide, x, y, w, h, fill=WHITE, radius=radius)
    gradient(s, stops, angle)
    return s


def text(slide, x, y, w, h, content, size=14, color=INK, bold=False, font=None, align="l",
         anchor="t", spacing=None, line_spacing=1.08, italic=False, margin=0.0, space_after=0):
    """
    Text box. `content` is a string or a list of paragraphs, each paragraph being
    either a string, a dict(text=..., size=..., bold=..., color=..., space_after=..., align=..., spacing=..., font=...)
    or a dict with runs=[{text, size, bold, color, ...}, ...].
    """
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    paragraphs = content if isinstance(content, list) else [content]
    for i, para in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if isinstance(para, str):
            para = {"text": para}
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[para.get("align", align)]
        p.line_spacing = para.get("line_spacing", line_spacing)
        p.space_after = Pt(para.get("space_after", space_after))
        runs = para.get("runs", [dict(para)])
        for rd in runs:
            r = p.add_run()
            r.text = rd.get("text", "")
            f = r.font
            f.name = rd.get("font", font or FONT_BODY)
            f.size = Pt(rd.get("size", para.get("size", size)))
            f.bold = rd.get("bold", para.get("bold", bold))
            f.italic = rd.get("italic", para.get("italic", italic))
            f.color.rgb = rgb(rd.get("color", para.get("color", color)))
            sp = rd.get("spacing", para.get("spacing", spacing))
            if sp:
                r._r.get_or_add_rPr().set("spc", str(int(sp * 100)))
    return tb


def label(slide, x, y, w, txt, color=VIOLET, size=9, align="l", h=0.25):
    """Small, bold, letter-spaced uppercase label (the deck's signature detail)."""
    return text(slide, x, y, w, h, txt.upper(), size=size, color=color, bold=True, spacing=1.6, align=align, anchor="m")


def title(slide, txt, dark=False, sub=None, y=0.55, size=32, w=10.2, sub_w=None):
    n_lines = txt.count("\n") + 1
    text(slide, MARGIN, y, w, 0.56 * n_lines + 0.1, txt, size=size, bold=True, font=FONT_HEAD,
         color=WHITE if dark else INK, anchor="t", line_spacing=1.0)
    if sub:
        text(slide, MARGIN, y + 0.56 * n_lines + 0.14, sub_w or w, 0.6, sub, size=14,
             color=MUTED_D if dark else SLATE, line_spacing=1.15)


def footer(slide, section, tagline, n, dark=False):
    c = MUTED_D if dark else SLATE
    text(slide, MARGIN, SLIDE_H - 0.48, 8, 0.25,
         [{"runs": [{"text": section.upper(), "bold": True, "color": c, "size": 8, "spacing": 1.4},
                    {"text": "   |   " + tagline.upper(), "bold": False, "color": c, "size": 8, "spacing": 1.4}]}],
         anchor="m")
    text(slide, SLIDE_W - MARGIN - 0.8, 0.5, 0.8, 0.3, f"{n:02d}", size=11, bold=True,
         color=CYAN if dark else VIOLET, align="r", anchor="m")


def disc(slide, cx, cy, d, fill, txt=None, txt_color=WHITE, size=10, line=None, alpha=None):
    o = oval(slide, cx - d / 2, cy - d / 2, d, d, fill=fill, line=line, alpha=alpha)
    if txt is not None:
        text(slide, cx - d / 2, cy - d / 2, d, d, txt, size=size, bold=True, color=txt_color, align="c", anchor="m")
    return o


def pill(slide, x, y, txt, fill=VIOLET, color=WHITE, size=8, w=None, h=0.28, line=None):
    w = w or (0.085 * len(txt) * size / 8 + 0.3)
    rect(slide, x, y, w, h, fill=fill, radius=h / 2, line=line)
    text(slide, x, y, w, h, txt.upper(), size=size, bold=True, color=color, align="c", anchor="m", spacing=1.2)
    return w


def chip_row(slide, x, y, chips, max_x, gap=0.12, row_h=0.4, size=8):
    """Row of pills that wraps to a new line when it reaches max_x. chips = [(text, fill), ...]. Returns bottom y."""
    cx, cy = x, y
    for txt, fill in chips:
        w = 0.085 * len(txt) * size / 8 + 0.3
        if cx + w > max_x and cx > x:
            cx, cy = x, cy + row_h
        pill(slide, cx, cy, txt, fill=fill, color=NAVY if fill in (CYAN, MINT, AMBER) else WHITE, size=size, w=w)
        cx += w + gap
    return cy + 0.28


def glow(slide, cx, cy, r, color=VIOLET, strength=0.16):
    """Fake soft glow: three concentric translucent discs."""
    for k, a in ((1.0, strength * 0.35), (0.66, strength * 0.6), (0.4, strength)):
        oval(slide, cx - r * k, cy - r * k, 2 * r * k, 2 * r * k, fill=color, alpha=a)


def _image_size(path):
    """(width, height) for JPEG/PNG without PIL."""
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", head[16:24])
            return w, h
        f.seek(0)
        data = f.read()
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        i += 2 + seg_len
    return 16, 9


def picture(slide, key, x, y, w, h, focus=(0.5, 0.5), radius=None, placeholder_label=None):
    """Image cropped to fill the box (like CSS object-fit: cover). Falls back to a gradient placeholder."""
    path = IMG.get(key, key)
    if not os.path.exists(path):
        s = grad_rect(slide, x, y, w, h, [(0, VIOLET_DK, 1), (1, NAVY, 1)], angle=35, radius=radius)
        text(slide, x, y, w, h, placeholder_label or f"image: {os.path.basename(path)}",
             size=11, color=MUTED_D, align="c", anchor="m")
        return s
    iw, ih = _image_size(path)
    pic = slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
    ia, ba = iw / ih, w / h
    if ia > ba:                      # image wider than box → crop left/right
        vis = ba / ia
        pic.crop_left = (1 - vis) * focus[0]
        pic.crop_right = (1 - vis) * (1 - focus[0])
    else:                            # image taller → crop top/bottom
        vis = ia / ba
        pic.crop_top = (1 - vis) * focus[1]
        pic.crop_bottom = (1 - vis) * (1 - focus[1])
    if radius:
        geom = pic._element.spPr.find(qn("a:prstGeom"))
        geom.set("prst", "roundRect")
        for old in geom.findall(qn("a:avLst")):
            geom.remove(old)
        av = etree.SubElement(geom, qn("a:avLst"))
        gd = etree.SubElement(av, qn("a:gd"))
        gd.set("name", "adj")
        gd.set("fmla", f"val {int(100000 * radius / max(0.01, min(w, h)))}")
    return pic


def background(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(color)


def notes(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt.strip()


def hline(slide, x, y, w, color=LIGHT_3, weight=0.75):
    ln = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
    ln.line.color.rgb = rgb(color)
    ln.line.width = Pt(weight)
    return ln


def vline(slide, x, y, h, color=LIGHT_3, weight=0.75):
    ln = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x), Inches(y + h))
    ln.line.color.rgb = rgb(color)
    ln.line.width = Pt(weight)
    return ln


def table(slide, x, y, col_w, rows, header_fill=NAVY, header_color=WHITE, row_h=0.42, head_h=0.42,
          first_col_color=VIOLET, dark=False, size=10.5, zebra=True):
    """Hand-drawn table (full styling control). rows[0] is the header."""
    total_w = sum(col_w)
    rect(slide, x, y, total_w, head_h, fill=header_fill)
    cx = x
    for j, cell in enumerate(rows[0]):
        text(slide, cx + 0.12, y, col_w[j] - 0.2, head_h, cell.upper(), size=8.5, bold=True, color=header_color,
             spacing=1.2, anchor="m")
        cx += col_w[j]
    yy = y + head_h
    for i, row in enumerate(rows[1:]):
        fill = (NAVY_2 if i % 2 == 0 else NAVY) if dark else (LIGHT_2 if i % 2 == 0 else LIGHT)
        if not zebra:
            fill = NAVY_2 if dark else LIGHT_2
        rect(slide, x, yy, total_w, row_h, fill=fill)
        hline(slide, x, yy + row_h, total_w, color=NAVY_3 if dark else LIGHT_3)
        cx = x
        for j, cell in enumerate(row):
            is_first = j == 0
            text(slide, cx + 0.12, yy, col_w[j] - 0.2, row_h, cell, size=size,
                 bold=is_first, color=(first_col_color if is_first else (WHITE if dark else INK)), anchor="m",
                 line_spacing=1.0)
            cx += col_w[j]
        yy += row_h
    hline(slide, x, y + head_h, total_w, color=NAVY_3 if dark else LIGHT_3)
    return yy


# ──────────────────────────────────────────────────────────────────────────────
# 3. SPEC REGISTRY (drives the markdown companion document)
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Spec:
    n: int
    title: str
    layout: str
    notes: str
    elements: list = field(default_factory=list)


SPECS: list[Spec] = []


def register(n, title_, layout, notes_, elements):
    SPECS.append(Spec(n, title_, layout.strip(), notes_.strip(), elements))


# ──────────────────────────────────────────────────────────────────────────────
# 4. SLIDES
# ──────────────────────────────────────────────────────────────────────────────
def slide_cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    picture(s, "hero", 5.2, 0, SLIDE_W - 5.2, SLIDE_H, focus=(0.62, 0.5), placeholder_label="hero product render")
    # fade image into the left panel
    g = rect(s, 5.2, 0, 3.6, SLIDE_H, fill=NAVY)
    gradient(g, [(0, NAVY, 1.0), (0.55, NAVY, 0.55), (1, NAVY, 0.0)], angle=0)
    rect(s, 0, 0, 5.21, SLIDE_H, fill=NAVY)
    glow(s, 1.2, 6.6, 1.6, VIOLET, 0.22)

    rect(s, MARGIN, 1.15, 0.55, 0.07, fill=CYAN)
    text(s, MARGIN, 1.55, 5.0, 2.0, [{"text": "NEUROLINK", "size": 50, "bold": True, "color": WHITE, "spacing": 2},
                                    {"text": "WEAR", "size": 50, "bold": True, "color": WHITE, "spacing": 2}],
         font=FONT_HEAD, line_spacing=0.95)
    text(s, MARGIN, 3.75, 4.6, 1.0, "Predictive health intelligence,\nworn every day.", size=20, color="E4E4F4",
         line_spacing=1.15)
    text(s, MARGIN, 5.2, 4.6, 0.5, [{"runs": [
        {"text": "SMART WEARABLE", "color": CYAN}, {"text": "  +  ", "color": MUTED_D},
        {"text": "EDGE & CLOUD AI", "color": CYAN}, {"text": "  +  ", "color": MUTED_D},
        {"text": "CAREGIVER SAFETY", "color": CYAN}]}], size=9, bold=True, spacing=0.8, anchor="t", line_spacing=1.3)
    text(s, MARGIN, 6.75, 6, 0.3, "Investor pitch  ·  Prototype stage  ·  Giza, Egypt  ·  2026", size=9.5, color=MUTED_D)
    notes(s, """
Open with the one-liner: NeuroLink Wear is a smart band that watches the vital signs of the people we love and turns them into timely, understandable action — on the wrist, in the cloud and on a caregiver's phone.
Set expectations: this is a prototype-stage company; we will show what is built, what we have learned, and exactly what we need to reach a validated pilot.
Timing: 30 seconds. Do not read the slide — let the product render do the work.""")
    register(1, "Cover", """
Dark navy canvas. Left 39%: solid navy text panel with a short cyan accent bar, the wordmark in two 50 pt lines (NEUROLINK / WEAR, +2 pt tracking), a 20 pt sub-headline and a cyan tracked "SMART WEARABLE + EDGE + CLOUD AI + CAREGIVER SAFETY" strap-line. Right 61%: full-bleed product render (hero_band.jpg) with a horizontal navy→transparent gradient so the photo melts into the text panel. A soft violet glow sits bottom-left for depth.""",
             "n/a", ["hero_band.jpg (16:9, right 61% of the canvas, focus point 62% from the left)",
                     "Wordmark 50 pt bold, subtitle 20 pt, strap-line 9.5 pt tracked",
                     "Navy→transparent gradient overlay (3.6 in wide) at the photo's left edge"])


def slide_problem(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "Critical health changes happen\nbetween check-ins",
          sub="A wearable can close the gap between an isolated reading and a timely response.", w=7.6)
    rows = [
        ("1", VIOLET, "Signals lack context",
         "Heart rate, oxygen, temperature and stress indicators only become meaningful when patterns are tracked together over time."),
        ("2", INDIGO, "Early warning is difficult",
         "Fatigue, fever, panic and low oxygen begin as subtle deviations — rarely as one obvious event."),
        ("3", PINK, "Emergencies need escalation",
         "A fall or a dangerous reading needs a prompt to the wearer and, if there is no answer, an automatic call for help."),
    ]
    y = 2.55
    for num, col, head, body in rows:
        disc(s, MARGIN + 0.25, y + 0.22, 0.44, col, num, size=11)
        text(s, MARGIN + 0.75, y - 0.02, 2.75, 0.7, head, size=15, bold=True, color=INK, anchor="t", line_spacing=1.05)
        text(s, MARGIN + 3.6, y - 0.02, 3.75, 0.9, body, size=11, color=SLATE, line_spacing=1.2)
        if num != "3":
            hline(s, MARGIN + 0.75, y + 1.05, 6.6)
        y += 1.3
    # stat column
    x0 = 8.55
    rect(s, x0, 1.0, SLIDE_W - MARGIN - x0, 5.7, fill=NAVY, radius=0.18)
    glow(s, SLIDE_W - MARGIN - 1.05, 5.65, 0.9, VIOLET, 0.28)
    label(s, x0 + 0.4, 1.35, 3.5, "Why it matters", color=CYAN)
    stats = [
        (FACTS["who_deaths"], "people die from falls every year worldwide — the second leading cause of unintentional injury death (WHO)."),
        (FACTS["who_lmic"], "of fall deaths occur in low- and middle-income countries such as Egypt (WHO)."),
        (FACTS["eg_60plus"], f"Egyptians are aged 60+ ({FACTS['eg_60plus_pct']} of the population) and the share keeps rising (CAPMAS 2024)."),
    ]
    y = 1.8
    for big, small in stats:
        text(s, x0 + 0.4, y, 3.6, 0.7, big, size=34, bold=True, color=WHITE, font=FONT_HEAD)
        text(s, x0 + 0.4, y + 0.72, 3.55, 0.85, small, size=10.5, color=MUTED_D, line_spacing=1.2)
        y += 1.6
    footer(s, "Problem", "Continuous context and response", 2)
    notes(s, """
Three failure modes of today's care: no context (a single number tells you nothing), no early warning (deterioration is gradual), and no escalation (a fall at home is only discovered hours later).
Anchor with the WHO numbers: an estimated 684 000 fatal falls a year, over 80% of them in low- and middle-income countries; 37.3 million falls a year need medical attention. Adults over 60 suffer the greatest number of fatal falls. (WHO fact sheet on falls, 2021.)
Localise: Egypt's 60+ population reached 9.3 million in 2024 — 8.8% of Egyptians — according to CAPMAS. Most live at home with family who work during the day.
Transition: "We built one system that senses, understands and responds."
Source URLs for the appendix: who.int/news-room/fact-sheets/detail/falls; globalissues.org/news/2024/10/24/38051 (CAPMAS figures).""")
    register(2, "Problem", """
Light canvas, two columns. Left 60%: 32 pt two-line headline, 14 pt sub-line, then three numbered rows (0.44 in coloured discs: violet, indigo, pink) with a 15 pt bold claim and an 11 pt slate explanation, separated by hairlines. Right 33%: a rounded navy stat card with a cyan "WHY IT MATTERS" label and three 34 pt statistics (684 000 · 80%+ · 9.3 M) each with a 10.5 pt caption. Footer tag "PROBLEM | CONTINUOUS CONTEXT AND RESPONSE", slide number top-right in violet.""",
             "see notes", ["Numbered disc rows (3)", "Navy stat card with 3 KPIs", "Hairline dividers"])


def slide_solution(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    title(s, "One system senses, explains\nand responds", dark=True, w=8)
    picture(s, "elder", MARGIN, 2.0, 4.9, 4.5, focus=(0.7, 0.45), radius=0.2, placeholder_label="wearer at home")
    steps = [
        ("1", CYAN, "Sense", "PPG, GSR, motion, skin temperature and GPS create a continuous, multi-signal view of the wearer."),
        ("2", VIOLET, "Understand", "Edge features and anomaly models separate a normal day from stress, fever, low oxygen, fatigue — or a fall."),
        ("3", MINT, "Respond", "The band asks \"Are you OK?\"; the app explains the signal, advises the next step and escalates danger to caregivers with location."),
    ]
    x0, y = 6.1, 2.15
    for num, col, head, body in steps:
        text(s, x0, y - 0.05, 0.5, 0.5, num, size=22, bold=True, color=col, font=FONT_HEAD)
        label(s, x0 + 0.6, y, 4, head, color=col, size=10)
        text(s, x0 + 0.6, y + 0.32, 6.0, 1.0, body, size=12.5, color="E4E4F4", line_spacing=1.2)
        if num != "3":
            hline(s, x0 + 0.6, y + 1.25, 6.0, color=NAVY_3)
        y += 1.5
    footer(s, "Solution", "Device, intelligence and action", 3, dark=True)
    notes(s, """
The product is a loop, not a gadget: sense → understand → respond.
Sense: five sensors on one wrist give a richer picture than any single metric. Understand: light features are computed on the band itself; anomaly and time-series models run in the cloud. Respond: the band talks to the wearer first — a simple "Are you OK?" — and only then escalates to family with a location link.
Emphasise dignity: the wearer stays in control; escalation happens only when they cannot answer.""")
    register(3, "Solution", """
Dark canvas. Headline top-left (2 lines). Left: rounded-corner lifestyle photo (elder_home.jpg, 4.9 × 4.5 in). Right: three stacked steps — big coloured numeral (cyan / violet / mint), tracked uppercase step name and a 12.5 pt description — separated by dark hairlines. Footer "SOLUTION | DEVICE, INTELLIGENCE AND ACTION".""",
             "see notes", ["elder_home.jpg rounded 0.2 in", "3 step blocks with coloured numerals"])


def slide_hardware(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    title(s, "Five sensors, one wrist", dark=True,
          sub="Each signal answers a different question; the AI layer combines them when one metric is not enough.", w=8.5, sub_w=11.5)
    picture(s, "exploded", MARGIN, 2.05, 4.6, 4.55, focus=(0.5, 0.5), radius=0.2, placeholder_label="exploded product view")
    rows = [
        ("Sensor", "Measures", "Role in the system"),
        ("MAX30102 PPG", "Heart rate · SpO₂ · HRV (RMSSD)", "Cardiovascular context, oxygen, recovery"),
        ("GSR electrodes", "Skin conductance (µS)", "Stress & sympathetic arousal"),
        ("MPU6050 IMU", "Acceleration · rotation", "Steps, tremor, impact & fall detection"),
        ("MLX90614 IR", "Skin & ambient temperature", "Fever trend, thermal change"),
        ("NEO-6M GPS", "Position · UTC time", "Location for safety escalation"),
    ]
    yy = table(s, 5.6, 2.05, [1.6, 2.5, 3.05], rows, header_fill=VIOLET, dark=True, first_col_color=CYAN, row_h=0.46, head_h=0.4)
    bottom = chip_row(s, 5.6, yy + 0.35, [("ESP32 dual-core", INDIGO), ("OLED prompt", VIOLET), ("one button: I'm OK / SOS", PINK),
                                          ("Wi-Fi · TLS MQTT", CYAN), ("Li-Po · USB-C", MINT)], max_x=SLIDE_W - MARGIN)
    text(s, 5.6, bottom + 0.2, 7.1, 0.5, "Wellness and safety insights — not a diagnostic medical device. Off-the-shelf modules today; a custom PCB is part of the roadmap.",
         size=9.5, color=MUTED_D, italic=True, line_spacing=1.2)
    footer(s, "Hardware", "Core sensor stack", 4, dark=True)
    notes(s, """
Walk the table top to bottom in one breath each: PPG for heart rate, oxygen and heart-rate variability; GSR for arousal; the IMU for steps, tremor and impacts; the IR thermometer for fever trends; GPS for location when it matters.
Everything hangs off a dual-core ESP32 — one core samples sensors and drives the OLED and button, the other handles Wi-Fi, TLS and MQTT.
Be candid: the prototype uses off-the-shelf modules; industrial design and a custom PCB are in the roadmap, and the band is positioned as a wellness/safety product, not a diagnostic device.""")
    register(4, "Hardware", """
Dark canvas. Headline + sub-line. Left: rounded exploded-view render (exploded_band.jpg, 4.6 × 4.55 in). Right: hand-drawn 3-column table (violet header, zebra navy rows, cyan first column) listing the five sensors; below it a row of colour-coded chips (ESP32, OLED, button, Wi-Fi/TLS, battery) and a 9.5 pt italic disclaimer. Footer "HARDWARE | CORE SENSOR STACK".""",
             "see notes", ["exploded_band.jpg", "Sensor table (5 rows)", "Component chips", "Disclaimer"])


def slide_architecture(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "System architecture", sub="A continuous pipeline turns raw sensor data into understandable guidance and safety actions.")
    stages = [
        ("Sensors", INDIGO, ["PPG · GSR · IMU", "Temperature · GPS", "up to 100 samples / s"]),
        ("ESP32 edge", VIOLET, ["HR · HRV · SpO₂ · steps", "Fall verification + prompt", "Telemetry every 2 s"]),
        ("AI core", "8B5CF6", ["Isolation Forest + LSTM AE", "Rule-based conditions", "LLM explanation"]),
        ("App + caregivers", MINT, ["Live vitals · trends · advice", "Alerts · emergency contacts", "GPS link on escalation"]),
    ]
    cw, gap, y0, ch = 2.55, 0.55, 2.3, 2.5
    x = MARGIN + 0.1
    for i, (name, col, lines) in enumerate(stages):
        rect(s, x, y0, cw, ch, fill=WHITE, line=LIGHT_3, radius=0.16)
        rect(s, x, y0, cw, 0.12, fill=col, radius=0.06)
        label(s, x + 0.25, y0 + 0.35, cw - 0.4, name, color=col if col != MINT else "0F9F6E", size=10)
        text(s, x + 0.25, y0 + 0.8, cw - 0.45, 1.5, [{"text": t, "space_after": 5} for t in lines], size=11, color=SLATE, line_spacing=1.15)
        if i < 3:
            arrow_right(s, x + cw + 0.12, y0 + ch / 2 - 0.16, 0.32, 0.32, fill=VIOLET)
        x += cw + gap
    # transport pill
    pill(s, (SLIDE_W - 8.4) / 2, y0 + ch + 0.3, "MQTT over TLS 1.2  ·  HiveMQ Cloud  ·  JSON ≤ 1 KB  ·  every 2 s  ·  alerts back to the band", fill=NAVY, size=8.5, w=8.4, h=0.32)
    # three support notes
    notes_ = [("Edge", "RMSSD, motion variance, tremor frequency and impact peaks computed on the wrist"),
              ("Fallback", "Statistical threshold rules keep working if the cloud or a model is unavailable"),
              ("Resilience", "Offline outbox: emergency packets are retried for 10 minutes; last-will status for presence")]
    x = MARGIN + 0.1
    for head, body in notes_:
        pill(s, x, 5.8, head, fill=NAVY, size=8, w=1.05)
        text(s, x, 6.15, 3.85, 0.7, body, size=10, color=SLATE, line_spacing=1.2)
        x += 4.05
    footer(s, "Technology", "Edge-to-cloud data pipeline", 5)
    notes(s, """
Left to right: sensors sample at up to 100 Hz; the ESP32 reduces that to physiologically meaningful features and publishes a compact JSON packet every two seconds over TLS to a managed MQTT broker (HiveMQ Cloud).
The AI core (FastAPI service) runs an Isolation Forest for point anomalies, an LSTM autoencoder for temporal anomalies, a rule-based condition classifier, and an optional LLM layer that writes the explanation and advice. Decisions flow back down the same broker to the band and the dashboard.
Design principle: the time-critical decisions (fall verification, the "Are you OK?" prompt) never depend on the cloud; the cloud adds insight, not safety-critical latency.""")
    register(5, "Architecture", """
Light canvas. Four white rounded stage cards (2.55 in wide) with coloured top bars (indigo → violet → purple → mint), tracked labels and three 11 pt bullet-like lines each; violet right-arrows between cards. Under the cards a navy transport pill ("MQTT over TLS 1.2 · HiveMQ Cloud · JSON ≤ 1 KB · every 2 s · alerts back to the band"). Bottom row: three navy mini-pills (EDGE / FALLBACK / RESILIENCE) with 10 pt explanations. Footer "TECHNOLOGY | EDGE-TO-CLOUD DATA PIPELINE".""",
             "see notes", ["4 stage cards + arrows", "Transport pill", "3 support notes"])


def slide_edge(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    title(s, "The wrist does the time-critical work", dark=True,
          sub="Firmware v1.0 turns raw samples into clinical-style features and a verified safety prompt — with or without the cloud.", w=9)
    tiles = [
        ("Heart rate & HRV", "Beat-to-beat intervals with artifact rejection; RMSSD over the last 20 beats.", CYAN),
        ("SpO₂ estimate", "Ratio-of-ratios on rolling red/IR AC-DC with perfusion and contact checks.", VIOLET),
        ("Fall detector", "Impact > 3 g, free-fall cue, orientation change and a 4 s immobility check → confidence score.", PINK),
        ("Motion analytics", "Pedometer, cadence, variance and dominant tremor frequency from 50 Hz IMU data.", INDIGO),
        ("Resilient link", "TLS MQTT, retained presence, offline outbox with 10-minute retry for emergencies.", MINT),
        ("Honest data", "Validity flags for every vital; missing sensors are reported, never faked.", AMBER),
    ]
    tw, th, gx, gy = 2.62, 1.75, 0.2, 0.2
    x0, y0 = MARGIN, 2.2
    for i, (head, body, col) in enumerate(tiles):
        r, c = divmod(i, 3)
        x, y = x0 + c * (tw + gx), y0 + r * (th + gy)
        rect(s, x, y, tw, th, fill=NAVY_2, radius=0.14)
        rect(s, x, y + 0.3, 0.06, th - 0.6, fill=col)
        text(s, x + 0.28, y + 0.25, tw - 0.45, 0.5, head, size=13, bold=True, color=WHITE)
        text(s, x + 0.28, y + 0.72, tw - 0.45, 1.0, body, size=10, color=MUTED_D, line_spacing=1.2)
    # on-device screen mock
    sx, sy, sw, sh = 9.45, 2.2, 3.3, 2.05
    glow(s, sx + sw / 2, sy + sh / 2, 1.3, CYAN, 0.10)
    rect(s, sx, sy, sw, sh, fill="05050F", line=NAVY_3, line_w=1.5, radius=0.12)
    label(s, sx + 0.25, sy + 0.2, 2.5, "Fall detected", color=PINK, size=9)
    text(s, sx + 0.25, sy + 0.5, 2.0, 0.5, "Are you OK?", size=20, bold=True, color=WHITE, font=FONT_HEAD)
    text(s, sx + sw - 1.05, sy + 0.42, 0.85, 0.7, "27", size=30, bold=True, color=CYAN, align="r", font=FONT_HEAD)
    rect(s, sx + 0.25, sy + 1.25, sw - 0.5, 0.08, fill=NAVY_3, radius=0.04)
    rect(s, sx + 0.25, sy + 1.25, (sw - 0.5) * 0.9, 0.08, fill=CYAN, radius=0.04)
    text(s, sx + 0.25, sy + 1.45, sw - 0.5, 0.4, "press button = I'm OK   ·   no answer in 30 s → help is called", size=8, color=MUTED_D)
    text(s, sx, sy + sh + 0.15, sw, 0.3, "On-device prompt (SSD1306 OLED)", size=9, color=MUTED_D, align="c")
    # verification badge
    rect(s, sx, 4.95, sw, 1.15, fill=NAVY_2, radius=0.14)
    text(s, sx + 0.25, 5.05, sw - 0.4, 0.4, f"{FACTS['checks']} automated logic checks", size=13, bold=True, color=WHITE)
    text(s, sx + 0.25, 5.45, sw - 0.4, 0.6, "HR ±0.1 bpm · exact RMSSD · fall vs. walking · step counts · JSON contract · prompt → ack / timeout → emergency",
         size=9, color=MUTED_D, line_spacing=1.2)
    footer(s, "Firmware", "ESP32 edge intelligence", 6, dark=True)
    notes(s, """
This is our technical moat at this stage: the band already produces the exact feature vector the models were trained on, and it verifies falls locally — impact, free-fall cue, orientation change and a four-second immobility check — before it ever prompts the wearer.
Everything time-critical is on the wrist; the cloud can be slow or offline and the safety loop still completes (emergency packets are queued and retried for ten minutes).
Validation so far is host-side: the firmware compiles against the real sensor and MQTT libraries and passes 87 automated behavioural checks on synthetic data. Bench and on-body validation is the next milestone — say so before anyone asks.""")
    register(6, "Edge intelligence", """
Dark canvas. Left two-thirds: 3 × 2 grid of navy tiles (2.62 × 1.75 in) each with a coloured left accent bar, 13 pt bold feature name and 10 pt description. Right third: a mock of the band's OLED prompt (near-black rounded panel, pink "FALL DETECTED" label, "Are you OK?" 20 pt, cyan 30 pt countdown "27", a 90 % cyan progress bar and an 8 pt hint), with a subtle cyan glow behind it; below it a navy badge "87 automated logic checks". Footer "FIRMWARE | ESP32 EDGE INTELLIGENCE".""",
             "see notes", ["6 feature tiles", "OLED prompt mock", "Verification badge"])


def slide_ai(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "The intelligence engine combines\nanomalies, trends and context", w=9)
    rows = [
        ("Condition", "Signal pattern", "Detection approach"),
        ("Stress", "HRV ↓ · GSR ↑ · temperature ↑", "Combined anomaly score"),
        ("Panic attack", "Heart-rate spike · GSR spike · no motion", "Sudden deviation + context"),
        ("Fever", "Temperature rising over time", "Continuous trend"),
        ("Low oxygen", "SpO₂ below threshold", "Threshold rule (fallback-safe)"),
        ("Fatigue", "Sustained low HRV", "Long-term trend analysis"),
        ("Fall", "Impact + immobility (edge-verified)", "IMU rule + LSTM motion anomaly"),
    ]
    table(s, MARGIN, 2.3, [1.55, 3.35, 2.75], rows, header_fill=VIOLET, row_h=0.47, head_h=0.42)
    x0 = 8.75
    label(s, x0, 2.3, 4, "Model stack", color=VIOLET, size=10)
    stack = [
        ("1", "Isolation Forest", "Point anomalies across 23 engineered features", VIOLET),
        ("2", "LSTM autoencoder", "Temporal anomalies over rolling windows (threshold 0.33 reconstruction error)", INDIGO),
        ("3", "Rule-based classifier", "Explainable condition labels; safe fallback if a model is unavailable", CYAN),
        ("4", "LLM layer", "Plain-language explanation and personalised next steps (optional, non-blocking)", MINT),
    ]
    y = 2.75
    for num, head, body, col in stack:
        disc(s, x0 + 0.2, y + 0.2, 0.36, col, num, size=10, txt_color=NAVY if col in (CYAN, MINT) else WHITE)
        text(s, x0 + 0.6, y - 0.02, 3.5, 0.35, head, size=13, bold=True, color=INK)
        text(s, x0 + 0.6, y + 0.3, 3.5, 0.7, body, size=10, color=SLATE, line_spacing=1.2)
        y += 0.98
    text(s, MARGIN, 6.05, 7.6, 0.5, f"Trained on {FACTS['dataset_rows']} labelled readings across five activity states (resting, sleeping, walking, exercising, running). "
         "Activity intensity, HR deviation, SpO₂ and fever risk scores are derived per reading.", size=10, color=SLATE, line_spacing=1.2)
    footer(s, "AI / ML", "Anomaly detection and explanation", 7)
    notes(s, """
Each condition maps to a signal pattern and a detection approach — this is why five sensors matter: stress is HRV down plus GSR up plus temperature up, not any one of them.
The stack is layered for robustness: Isolation Forest for point anomalies, an LSTM autoencoder for temporal drift, a rule-based classifier that always produces an explainable label, and an optional LLM that only writes the explanation — it never makes the safety decision.
Data today: 1,875 labelled readings across five activity states, with derived features such as HR deviation from the expected value for the current activity. The pilot will replace synthetic/lab data with real-world wear data — that is the single most valuable asset we will build next.""")
    register(7, "Intelligence engine", """
Light canvas. Left 62%: 3-column condition table (violet header, six zebra rows, violet first column). Right: "MODEL STACK" label and four rows — coloured numbered disc, 13 pt model name, 10 pt role. Bottom-left: 10 pt data provenance line. Footer "AI / ML | ANOMALY DETECTION AND EXPLANATION".""",
             "see notes", ["Condition table (6 rows)", "Model stack (4)", "Data provenance line"])



def slide_ai_architecture(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "AI architecture — from sensor to alert", w=10.4,
          sub="A target end-to-end path: wearable signals → context → detection → understandable action.")
    pill(s, 9.9, 1.86, "Design path · validation in progress", fill=NAVY, color=WHITE, size=7.4, w=2.8, h=0.31)
    stages = [
        ("ESP32 band", "5 vital-sign sensors\nMotion + GPS", "6A3CE8"),
        ("Normalize", "Check units\nBuild features", INDIGO),
        ("Activity", "Random Forest\nContext, not alert", "1676B8"),
        ("Calibrate", "EWMA baseline\nCrisis-gated", "0E8F72"),
        ("Detect", "Clinical floors\nPersonal σ + ML", VIOLET),
        ("Explain + deliver", "Plain-language alert\nLive dashboard", "D96D36"),
    ]
    x0, y0, cw, ch, gap = 0.62, 2.65, 1.82, 2.15, 0.32
    for i, (head, body, col) in enumerate(stages):
        x = x0 + i * (cw + gap)
        rect(s, x, y0, cw, ch, fill=WHITE, line=LIGHT_3, radius=0.14)
        rect(s, x, y0, cw, 0.1, fill=col, radius=0.05)
        disc(s, x + 0.27, y0 + 0.42, 0.34, col, str(i + 1), size=9)
        text(s, x + 0.16, y0 + 0.74, cw - 0.3, 0.48, head, size=12.2, bold=True, color=INK, line_spacing=1.0)
        text(s, x + 0.16, y0 + 1.28, cw - 0.3, 0.72, body, size=9.6, color=SLATE, line_spacing=1.15)
        if i < len(stages) - 1:
            arrow_right(s, x + cw + 0.045, y0 + 0.91, 0.23, 0.28, fill=VIOLET)
    rect(s, 0.62, 5.18, 12.12, 0.94, fill=NAVY, radius=0.14)
    label(s, 0.9, 5.35, 2.2, "Decision principle", color=CYAN, size=8.5)
    text(s, 3.05, 5.31, 9.3, 0.55,
         "A model may add context; it never replaces a wearer-first safety workflow.",
         size=15, bold=True, color=WHITE, anchor="m")
    text(s, 0.65, 6.3, 12.0, 0.35,
         "Integration note: align device MQTT topic / cloud broker with the API subscription before live end-to-end demos.",
         size=9.2, color=SLATE, italic=True)
    footer(s, "AI architecture", "Sensor-to-alert pathway", 8)
    notes(s, """
Walk left to right: the band supplies sensor readings; the backend normalizes and derives features, predicts activity context, updates an intended personal baseline, evaluates the alert paths, and delivers an explanation to the dashboard.
Status matters: the EWMA calibration and fully independent three-tier OR policy on the next slides are the target design and require integration/validation; do not describe them as shipped until wired and tested.
The current repository also has an integration mismatch to resolve before a live demo: firmware publishes to a cloud topic while main.py subscribes to a local broker/topic. The WebSocket dashboard path exists, but the end-to-end broker contract needs alignment.""")
    register(8, "AI architecture — from sensor to alert", """
Light canvas. Six horizontal rounded stage cards with colored top accents and numbered discs: ESP32 band → normalize → activity classifier → personal calibration → detection → explanation/dashboard. Violet arrows connect stages. Dark decision-principle banner below; italic integration note. A top pill marks this as a design path under validation.
""", "see notes", ["6 editable pipeline stages", "Decision-principle banner", "Integration caveat"])


def slide_model_roles(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    title(s, "Two trained models, two different jobs", dark=True, w=10.2,
          sub="One recognizes movement context; the other looks for unusual multivariate readings.")
    cards = [
        (0.62, "CONTEXT MODEL", "Random Forest Activity Classifier", CYAN,
         "MOTION-ONLY INPUTS", "Accelerometer · gyroscope · step count",
         "Predicts sleeping, resting, walking, running or exercising. Its prediction is context—not an alert—and helps interpret what is normal for that activity.",
         "OUTPUT", "Activity label → expected context"),
        (6.83, "ANOMALY MODEL", "Isolation Forest", "F59E0B",
         "UNSUPERVISED · 23 FEATURES", "Vitals · motion · activity intensity",
         "Scores each live feature row for unusual combinations. A separate condition-mapping layer can translate a flagged anomaly into an explainable cause.",
         "OUTPUT", "Anomaly label + score"),
    ]
    for x, tag, head, col, inlabel, inputs, body, outlabel, output in cards:
        rect(s, x, 2.18, 5.88, 3.75, fill=NAVY_2, radius=0.18)
        pill(s, x + 0.28, 2.42, tag, fill=col, color=NAVY if col == CYAN else WHITE, size=7.6, w=1.7)
        text(s, x + 0.28, 2.92, 5.25, 0.55, head, size=18, bold=True, color=WHITE, font=FONT_HEAD)
        label(s, x + 0.28, 3.63, 4.8, inlabel, color=col, size=8.3)
        text(s, x + 0.28, 3.94, 5.2, 0.42, inputs, size=11.5, bold=True, color=WHITE)
        hline(s, x + 0.28, 4.48, 5.3, color=NAVY_3)
        text(s, x + 0.28, 4.63, 5.23, 0.73, body, size=10.5, color=MUTED_D, line_spacing=1.18)
        label(s, x + 0.28, 5.43, 1.1, outlabel, color=col, size=8)
        text(s, x + 1.36, 5.38, 4.1, 0.38, output, size=10.5, bold=True, color=WHITE)
    rect(s, 0.62, 6.18, 12.09, 0.55, fill="262552", radius=0.12)
    text(s, 0.87, 6.22, 11.6, 0.38,
         "Both score a single live row without a rolling history; the LSTM autoencoder separately handles temporal windows.",
         size=10, color=MUTED_D, align="c", anchor="m")
    footer(s, "AI / ML", "Model roles and inference", 9, dark=True)
    notes(s, """
The Random Forest receives seven motion inputs only: accelerometer axes, gyroscope axes and step count. It predicts one of five activity classes. That label informs context; it is not itself an alert.
The Isolation Forest is unsupervised and consumes the 23-feature numeric row (vitals, motion, engineered signals and activity intensity). It returns an anomaly score for a single reading. The condition mapper adds a label after the anomaly decision.
These two models do not need a rolling buffer for inference. Separately, the existing LSTM autoencoder uses a ten-reading window, so avoid claiming that every model is memoryless.""")
    register(9, "Two trained models, two different jobs", """
Dark canvas. Two large navy cards side by side: cyan context-model card for Random Forest with motion-only inputs, five activity classes and a clear “context, not alert” role; amber Isolation Forest card with unsupervised 23-feature input and anomaly-score output. Bottom banner distinguishes both single-row models from the separate rolling-window LSTM.
""", "see notes", ["Random Forest activity card", "Isolation Forest anomaly card", "Inference-window caveat"])


def slide_model_results(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "Promising offline results —\nwith validation still ahead", w=9.1,
          sub="Held-out evaluation: 375 readings from a 1,875-reading dataset.")
    # Main metrics panel
    rect(s, 0.62, 2.25, 5.55, 3.62, fill=NAVY, radius=0.18)
    label(s, 0.95, 2.52, 4.5, "Activity classifier · held-out set", color=CYAN, size=8.5)
    text(s, 0.95, 2.95, 2.4, 0.82, "94%", size=39, bold=True, color=WHITE, font=FONT_HEAD)
    text(s, 3.3, 3.0, 2.35, 0.72, "accuracy", size=14, bold=True, color=MUTED_D, anchor="m")
    hline(s, 0.95, 3.92, 4.9, color=NAVY_3, weight=1.1)
    text(s, 0.95, 4.16, 2.4, 0.78, "0.94", size=34, bold=True, color=CYAN, font=FONT_HEAD)
    text(s, 3.3, 4.22, 2.35, 0.65, "macro F1", size=14, bold=True, color=MUTED_D, anchor="m")
    text(s, 0.95, 5.16, 4.85, 0.42, "375 test readings · 5 activity classes", size=10, color=MUTED_D)
    # Class performance list
    rect(s, 6.42, 2.25, 6.29, 3.62, fill=WHITE, line=LIGHT_3, radius=0.18)
    label(s, 6.75, 2.52, 5.2, "Per-class F1", color=VIOLET, size=8.5)
    class_rows = [("Sleeping + resting", "≈0.99", MINT), ("Walking", "0.97", CYAN),
                  ("Running", "0.89", INDIGO), ("Exercising", "0.85", AMBER)]
    yy = 2.95
    for name, score, col in class_rows:
        text(s, 6.75, yy, 2.8, 0.38, name, size=11.2, bold=True, color=INK, anchor="m")
        rect(s, 9.55, yy + 0.09, 1.85, 0.16, fill=LIGHT_3, radius=0.08)
        rect(s, 9.55, yy + 0.09, 1.85 * float(score.replace("≈", "")), 0.16, fill=col, radius=0.08)
        text(s, 11.55, yy, 0.8, 0.38, score, size=11.5, bold=True, color=col, align="r", anchor="m")
        yy += 0.58
    # Isolation Forest strip
    rect(s, 0.62, 6.03, 12.09, 0.68, fill="EEEFF8", radius=0.12)
    text(s, 0.88, 6.1, 2.35, 0.5, "ISOLATION FOREST", size=9, bold=True, color=VIOLET, anchor="m")
    text(s, 3.0, 6.1, 2.0, 0.5, "37 / 375 flagged", size=10.5, bold=True, color=INK, anchor="m")
    text(s, 5.03, 6.1, 3.4, 0.5, "35 mapped · 18 low oxygen · 17 fever", size=9.8, color=INK, anchor="m")
    text(s, 8.62, 6.1, 1.7, 0.5, "2 unresolved", size=9.8, bold=True, color=SLATE, anchor="m")
    pill(s, 10.55, 6.19, "≈10% flagged", fill=VIOLET, size=7.3, w=1.75, h=0.28)
    text(s, 0.65, 6.77, 11.9, 0.2,
         "Offline dataset metrics only — not clinical validation or a claim of real-world sensitivity.",
         size=8.7, color=SLATE, italic=True)
    footer(s, "AI / ML", "Preliminary model evaluation", 10)
    notes(s, """
Use these as preliminary offline results, not a clinical claim. The activity classifier was evaluated on 375 held-out readings: 94% accuracy and 0.94 macro F1. Sleeping and resting are approximately 0.99 F1, walking 0.97, running 0.89 and exercising 0.85.
On the same-size held-out set, the Isolation Forest flagged 37 readings (about 9.9%). The condition mapping assigned 35 a cause: 18 low-oxygen and 17 fever; two remained unexplained.
Before presenting externally, reproduce these metrics from the exact split, verify no leakage between train and test, and state that the dataset evaluation is not an on-body or clinical validation study.""")
    register(10, "Model results", """
Light canvas. Left dark metric panel with 39 pt 94% accuracy and 34 pt 0.94 macro F1. Right white panel with four per-class F1 bars. Bottom lavender strip reports Isolation Forest counts (37/375 flagged, 35 mapped, 18 low oxygen, 17 fever, 2 unresolved). A small italic caveat says offline results are not clinical validation.
""", "see notes", ["Accuracy and macro-F1 KPIs", "Per-class F1 bars", "Isolation Forest outcome strip", "Validation caveat"])


def slide_equation_library(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "Equation library — documented, not learned", w=10.4,
          sub="Transparent score logic complements the trained models; it does not replace them.")
    pill(s, 10.2, 1.86, "Rules · pilot validation", fill=NAVY, size=7.5, w=2.45, h=0.31)
    top = [
        (0.62, "Stress index", "GSR arousal  +  HRV drop  +  resting-HR rise", "Combined signals; no single sensor decides alone.", VIOLET),
        (4.74, "Core temperature", "Tcore ≈ gain × Tskin + offset", "Calibrated estimate from the skin-temperature reading.", CYAN),
        (8.86, "Fever score", "Tcore  +  rate of rise  +  HR–temperature coupling", "Combines level, trend and physiological context.", AMBER),
    ]
    for x, head, formula, body, col in top:
        rect(s, x, 2.42, 3.85, 1.68, fill=WHITE, line=LIGHT_3, radius=0.16)
        rect(s, x, 2.42, 3.85, 0.09, fill=col, radius=0.045)
        text(s, x + 0.24, 2.68, 3.35, 0.36, head, size=14, bold=True, color=INK)
        text(s, x + 0.24, 3.08, 3.35, 0.46, formula, size=11.2, bold=True, color=col, line_spacing=1.05)
        text(s, x + 0.24, 3.58, 3.35, 0.42, body, size=9.2, color=SLATE, line_spacing=1.1)
    bottom = [
        (1.72, "Hypoxic burden", "Accumulated desaturation over time", "Temporal accumulation filters single noisy dips.", INDIGO),
        (6.98, "Fall signature", "Free-fall → impact (≥2.8 g) → tumble (≥2.4 rad/s) → stillness", "A sequence of motion cues, not an isolated acceleration peak.", PINK),
    ]
    for x, head, formula, body, col in bottom:
        rect(s, x, 4.35, 4.65, 1.58, fill=WHITE, line=LIGHT_3, radius=0.16)
        rect(s, x, 4.35, 4.65, 0.09, fill=col, radius=0.045)
        text(s, x + 0.24, 4.6, 4.15, 0.34, head, size=14, bold=True, color=INK)
        text(s, x + 0.24, 4.99, 4.15, 0.43, formula, size=11, bold=True, color=col, line_spacing=1.05)
        text(s, x + 0.24, 5.46, 4.15, 0.34, body, size=9.2, color=SLATE, line_spacing=1.1)
    text(s, 0.65, 6.32, 12.0, 0.35,
         "Deterministic by design · formula definitions and thresholds remain subject to bench and on-body validation.",
         size=9.2, color=SLATE, italic=True, align="c")
    footer(s, "AI / ML", "Transparent health-score logic", 11)
    notes(s, """
These are interpretable score definitions, not learned weights: stress combines electrodermal arousal, HRV drop and resting-HR rise; core temperature estimates from skin temperature through a gain/offset calibration; fever combines level, rate of rise and HR-temperature coupling; hypoxic burden accumulates desaturation over time to ignore isolated noisy dips; fall logic requires a sequence of motion cues.
The repository implements only part of this catalog today (for example, normalized stress, SpO2/fever risk features and local fall verification). Confirm each equation and threshold is wired, tested and clinically reviewed before describing the entire library as deployed.""")
    register(11, "Equation library — documented, not learned", """
Light canvas. Three compact white formula cards across the upper row (stress index, core-temperature estimate, fever score); two wider cards below (hypoxic burden and fall signature). Each has a colored top rule, bold name, large symbolic formula and one-line interpretation. Bottom caveat identifies validation status.
""", "see notes", ["5 formula cards", "Deterministic-vs-learned distinction", "Validation caveat"])


def slide_personal_calibration(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    title(s, "Personal calibration — learning\neach wearer’s baseline", dark=True, w=9.2,
          sub="A rolling reference makes deviations personal without letting a crisis redefine normal.")
    pill(s, 10.15, 1.86, "Pilot design", fill=CYAN, color=NAVY, size=7.5, w=2.25, h=0.31)
    rect(s, 0.62, 2.35, 5.45, 1.3, fill=NAVY_2, radius=0.16)
    label(s, 0.93, 2.56, 2.3, "EWMA update", color=CYAN, size=8.5)
    text(s, 0.93, 2.88, 4.85, 0.48, "Baselineₜ = α · readingₜ + (1 − α) · Baselineₜ₋₁", size=15, bold=True,
         color=WHITE, align="c", anchor="m")
    # Baseline channels
    text(s, 0.68, 3.92, 5.3, 0.35, "Each valid reading can refine these resting-state references:",
         size=10, color=MUTED_D)
    chip_row(s, 0.68, 4.37, [("HR", VIOLET), ("HRV", INDIGO), ("GSR", "0F9F6E"),
                             ("Temperature", "D96D36"), ("SpO₂", "1676B8")], max_x=6.0, size=8.5)
    # safeguards
    label(s, 6.55, 2.36, 5.6, "Three safeguards", color=CYAN, size=8.5)
    safeguards = [
        ("Automatic", "Recent valid readings carry more weight; one spike cannot reset the baseline.", CYAN),
        ("Crisis-gated", "Exclude readings during an active alert so illness is not learned as normal.", PINK),
        ("Caregiver-anchored", "A reference-device measurement can correct a personal sensor offset.", MINT),
    ]
    y = 2.76
    for head, body, col in safeguards:
        rect(s, 6.55, y, 6.16, 0.78, fill=NAVY_2, radius=0.12)
        rect(s, 6.55, y, 0.07, 0.78, fill=col, radius=0.035)
        text(s, 6.82, y + 0.1, 1.8, 0.28, head, size=11.5, bold=True, color=col)
        text(s, 8.65, y + 0.08, 3.78, 0.56, body, size=9.5, color=MUTED_D, anchor="m", line_spacing=1.12)
        y += 0.9
    # confidence maturity line
    text(s, 0.68, 5.38, 2.2, 0.32, "BASELINE CONFIDENCE", size=8.5, bold=True, color=MUTED_D, spacing=1.1)
    rect(s, 2.65, 5.49, 4.0, 0.12, fill=NAVY_3, radius=0.06)
    rect(s, 2.65, 5.49, 2.55, 0.12, fill=CYAN, radius=0.06)
    text(s, 2.65, 5.72, 1.5, 0.28, "warming_up", size=9, color=MUTED_D)
    text(s, 5.15, 5.72, 1.5, 0.28, "active", size=9, bold=True, color=CYAN, align="r")
    rect(s, 7.05, 5.46, 5.66, 0.68, fill="262552", radius=0.13)
    text(s, 7.32, 5.48, 5.12, 0.6,
         "Status progresses with reliable wear time; clinical floors remain universal.",
         size=10, color=WHITE, anchor="m", align="c")
    text(s, 0.65, 6.42, 12.0, 0.3,
         "Calibration is a target feature; validate update rate, exclusions and caregiver corrections before pilot use.",
         size=8.9, color=MUTED_D, italic=True)
    footer(s, "AI / ML", "Personalized reference signals", 12, dark=True)
    notes(s, """
Explain the EWMA intuitively: each new valid measurement nudges a personal reference, with recent readings weighted more heavily, rather than moving the baseline abruptly. Update HR, HRV, GSR, temperature and SpO2 references separately.
The safeguards are important: active-alert readings are excluded; a caregiver can anchor calibration using a reference device; and a confidence state stays warming_up until enough reliable wear data exist. Fixed clinical floors are never calibrated away.
Implementation status: this calibration policy is not yet wired into the current pipeline.py runtime. Present it as a pilot design/roadmap capability until the update loop, gating, persistence and tests are implemented.""")
    register(12, "Personal calibration — building each wearer’s baseline", """
Dark canvas. Left: EWMA formula panel and five baseline-channel chips, plus warming_up-to-active confidence bar. Right: three stacked safeguard cards (automatic, crisis-gated, caregiver-anchored) and a statement that clinical floors remain universal. Cyan “PILOT DESIGN” pill and bottom validation caveat.
""", "see notes", ["EWMA formula", "Five baseline channels", "Three safeguards", "Confidence progression"])


def slide_detection_tiers(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "Three independent detection tiers", w=9.6,
          sub="Activity informs context; any one safety path can raise an alert.")
    pill(s, 10.0, 1.86, "Target alert policy", fill=NAVY, size=7.5, w=2.55, h=0.31)
    # Activity context node
    rect(s, 4.72, 2.22, 3.9, 0.72, fill=NAVY, radius=0.14)
    label(s, 4.98, 2.31, 1.65, "Context", color=CYAN, size=7.5)
    text(s, 6.15, 2.28, 2.15, 0.48, "Activity classifier", size=14, bold=True, color=WHITE, anchor="m")
    # Branch connectors from context to three tiers
    center_x = 6.67
    hline(s, 2.58, 3.23, 8.18, color="A8A8B5", weight=1.4)
    vline(s, center_x, 2.94, 0.29, color="A8A8B5", weight=1.4)
    tiers = [
        (0.62, "01", "Clinical floors", "Fixed medical limits", "SpO₂ <90% · core temp ≥37.8°C\nFall impact ≥2.8 g", "1676B8"),
        (4.76, "02", "Personal σ-rules", "Per-activity baseline", "Deviation from the wearer’s\ncalibrated activity baseline", "0F9F6E"),
        (8.90, "03", "Trained ML model", "Isolation Forest", "23-feature anomaly score\nwith activity as an input", "D96D36"),
    ]
    card_y, card_w, card_h = 3.48, 3.82, 1.58
    for x, num, head, sub, body, col in tiers:
        vline(s, x + card_w / 2, 3.23, 0.25, color="A8A8B5", weight=1.25)
        rect(s, x, card_y, card_w, card_h, fill=WHITE, line=LIGHT_3, radius=0.16)
        rect(s, x, card_y, card_w, 0.09, fill=col, radius=0.045)
        disc(s, x + 0.34, card_y + 0.39, 0.36, col, num, size=8.5)
        text(s, x + 0.62, card_y + 0.2, 2.95, 0.34, head, size=13.4, bold=True, color=INK)
        text(s, x + 0.62, card_y + 0.55, 2.95, 0.27, sub, size=9.2, bold=True, color=col)
        text(s, x + 0.24, card_y + 0.98, card_w - 0.48, 0.47, body, size=9.1, color=SLATE, line_spacing=1.1)
    # OR convergence and alert node
    for x in (2.53, 6.67, 10.81):
        vline(s, x, 5.06, 0.31, color="A8A8B5", weight=1.3)
    hline(s, 2.53, 5.37, 8.28, color="A8A8B5", weight=1.3)
    vline(s, center_x, 5.37, 0.16, color="A8A8B5", weight=1.3)
    rect(s, 4.52, 5.53, 4.3, 0.7, fill=VIOLET, radius=0.16)
    text(s, 4.72, 5.58, 3.9, 0.56, "OR gate · any one tier fires → alert", size=15, bold=True, color=WHITE, align="c", anchor="m")
    text(s, 0.65, 6.42, 12.0, 0.28,
         "Safety principle: personal calibration cannot suppress a clinical floor. Target architecture · thresholds and independent paths require validation.",
         size=8.6, color=SLATE, italic=True, align="c")
    footer(s, "AI safety", "Independent detection paths", 13)
    notes(s, """
Describe the intended policy as three independent paths. Tier 1 is a fixed clinical floor (examples supplied: SpO2 under 90%, estimated core temperature at or above 37.8°C, fall impact at or above 2.8 g); personalization cannot disable it. Tier 2 evaluates deviation from the wearer’s per-activity baseline. Tier 3 is the Isolation Forest as a third opinion with activity in its feature vector. Any one tier should be sufficient to alert; OR, never AND.
Important implementation caveat: the current pipeline.py does not yet implement this exact independent OR policy. Today the IF anomaly gates the condition mapper, and IF/LSTM labels are combined into a confidence ensemble. Treat this slide as target architecture until the code is changed and threshold behavior is tested. Clinical limits and sensor-derived core temperature also require validation.""")
    register(13, "Three independent detection tiers", """
Light canvas. Activity-classifier context node at top branches to three colored tier cards: fixed clinical floors, personal per-activity sigma rules, and Isolation Forest. The three paths converge at a violet OR gate (“any one tier fires → alert”). Small “target alert policy” badge and bottom validation caveat.
""", "see notes", ["Activity-context node", "Three detection-tier cards", "OR gate", "Validation caveat"])

def slide_safety(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    picture(s, "elder", 7.9, 0, SLIDE_W - 7.9, SLIDE_H, focus=(0.72, 0.5), placeholder_label="wearer photo")
    g = rect(s, 7.9, 0, 2.2, SLIDE_H, fill=NAVY)
    gradient(g, [(0, NAVY, 1.0), (1, NAVY, 0.0)], angle=0)
    title(s, "A fall triggers a verified\nsafety workflow", dark=True, w=7)
    label(s, MARGIN, 1.75, 5, "Designed emergency escalation", color=CYAN, size=9.5)
    steps = [
        ("Detect", "Impact above 3 g, a free-fall cue, or a dangerous vital pattern from the AI core", CYAN),
        ("Verify", "Post-impact immobility (4 s), orientation change, severity and GPS fix → confidence", INDIGO),
        ("Prompt", "OLED asks \"Are you OK?\" — one button press ends it; caregivers see a pre-alert", VIOLET),
        ("Escalate", "No answer within 30 s → emergency packet: event, vitals, timestamp, Google Maps link", AMBER),
        ("Notify", "Backend dispatches to saved contacts; band shows HELP REQUESTED until acknowledged", PINK),
    ]
    y = 2.3
    vline(s, MARGIN + 0.25, y + 0.2, 4 * 0.86, color=NAVY_3, weight=1.5)
    for i, (head, body, col) in enumerate(steps):
        disc(s, MARGIN + 0.25, y + 0.2, 0.42, col, str(i + 1), size=10, txt_color=NAVY if col in (CYAN, AMBER) else WHITE)
        text(s, MARGIN + 0.8, y - 0.03, 1.4, 0.4, head, size=13.5, bold=True, color=WHITE)
        text(s, MARGIN + 2.1, y, 4.9, 0.8, body, size=10.5, color=MUTED_D, line_spacing=1.2)
        y += 0.86
    text(s, MARGIN, 6.55, 7, 0.4, "Escalation thresholds, consent flows and failure handling are validated in the pilot before any public launch.",
         size=9.5, color=MUTED_D, italic=True)
    footer(s, "Safety", "Designed emergency escalation", 14, dark=True)
    notes(s, """
Tell it as a story: the wearer falls in the kitchen at 11 a.m. The band feels a 4 g impact followed by four seconds without movement while lying down. The screen lights up: "Are you OK?" — 30 seconds to press the button. She cannot. The band publishes an emergency packet with her vitals, the time and a maps link; the backend notifies her daughter; the band shows HELP REQUESTED until someone acknowledges.
Two design choices matter to investors: the wearer is asked first (dignity and fewer false alarms), and the whole loop is deterministic and testable — no model in the critical path.
Be transparent about what is not yet validated: thresholds, consent and failure handling will be tuned in the pilot.""")
    register(14, "Safety workflow", """
Dark canvas with a full-height lifestyle photo on the right 41% (elder_home.jpg) fading into navy via a 2.2 in gradient. Left: two-line headline, cyan tracked sub-label, a vertical timeline of five numbered discs (cyan → indigo → violet → amber → pink) each with a 13.5 pt step name and 10.5 pt description. Italic caveat at the bottom. Footer "SAFETY | DESIGNED EMERGENCY ESCALATION".""",
             "see notes", ["Vertical 5-step timeline", "Photo with gradient fade", "Caveat line"])


def slide_app(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "Live data becomes clear action\nfor families", w=8)
    picture(s, "caregiver", MARGIN, 2.2, 5.3, 4.35, focus=(0.35, 0.5), radius=0.2, placeholder_label="caregiver app photo")
    label(s, 6.5, 2.2, 4, "Caregiver app & dashboard", color=VIOLET, size=10)
    items = [
        ("Live", "Current vitals, activity state and band presence — green means all good", CYAN),
        ("Trends", "HRV, temperature and anomaly history to catch slow deterioration", INDIGO),
        ("Advice", "LLM-written explanations and personalised next steps for the wearer", VIOLET),
        ("Alerts", "Stress, fever, low oxygen and fall notifications, graded by severity", AMBER),
        ("Safety", "Emergency contacts, GPS context and a full alert timeline", PINK),
    ]
    y = 2.65
    for head, body, col in items:
        rect(s, 6.5, y + 0.08, 0.08, 0.5, fill=col, radius=0.04)
        text(s, 6.75, y, 1.3, 0.35, head.upper(), size=10, bold=True, color=col if col not in (CYAN, AMBER) else INK, spacing=1.2)
        text(s, 8.0, y - 0.02, 4.7, 0.7, body, size=11.5, color=INK, line_spacing=1.2)
        hline(s, 6.75, y + 0.68, 5.9)
        y += 0.8
    footer(s, "Product", "Caregiver app and dashboard", 15)
    notes(s, """
The buyer is usually the adult child; the wearer is the parent. The app is built for the buyer's anxiety: a green circle that says "all good" is the feature people pay for every month.
Today: a live web dashboard already consumes the pipeline output; the mobile app is the next build item. Show the dashboard live if the demo network allows it.
Alert grading (low / medium / high / critical) maps directly to what the band shows on the wrist, so family and wearer always see the same truth.""")
    register(15, "Caregiver experience", """
Light canvas. Left: rounded photo (caregiver_app.jpg, 5.3 × 4.35 in). Right: violet tracked label and five rows — a thin coloured bar, 10 pt uppercase feature name (LIVE / TRENDS / ADVICE / ALERTS / SAFETY) and 11.5 pt description — separated by hairlines. Footer "PRODUCT | CAREGIVER APP AND DASHBOARD".""",
             "see notes", ["caregiver_app.jpg rounded", "5 feature rows"])


def slide_traction(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    title(s, "What is already built", dark=True, sub="Prototype stage — every layer of the stack exists end to end.")
    tiles = [
        (FACTS["dataset_rows"], "labelled readings", "5 activity states · 14 raw signals · 21 engineered features", VIOLET),
        ("3 + 1", "model pipeline", "Isolation Forest · LSTM autoencoder · rule classifier · optional LLM advice", INDIGO),
        ("v1.0", "ESP32 firmware", f"Full sensor stack, fall/SOS workflow, TLS MQTT — {FACTS['checks']} automated checks", CYAN),
        ("Live", "cloud path", "HiveMQ Cloud broker · FastAPI service · web dashboard", MINT),
    ]
    tw, gap = 2.85, 0.24
    x = MARGIN
    for big, unit, body, col in tiles:
        rect(s, x, 2.3, tw, 2.35, fill=NAVY_2, radius=0.16)
        rect(s, x, 2.3, tw, 0.1, fill=col, radius=0.05)
        text(s, x + 0.3, 2.6, tw - 0.5, 0.7, big, size=34, bold=True, color=WHITE, font=FONT_HEAD)
        label(s, x + 0.3, 3.3, tw - 0.5, unit, color=col, size=9.5)
        text(s, x + 0.3, 3.7, tw - 0.55, 0.9, body, size=10, color=MUTED_D, line_spacing=1.2)
        x += tw + gap
    # maturity timeline
    y = 5.55
    hline(s, MARGIN + 0.4, y, 11.3, color=NAVY_3, weight=2)
    phases = [("Concept", "system design, dataset, models", MUTED_D, False),
              ("Prototype", "firmware + cloud + dashboard", CYAN, True),
              ("Pilot", "30–50 households, 3 months", MUTED_D, False),
              ("Launch", "Egypt, then MENA", MUTED_D, False)]
    x = MARGIN + 0.4
    for name, desc, col, now in phases:
        disc(s, x, y, 0.3 if now else 0.2, col)
        if now:
            oval(s, x - 0.3, y - 0.3, 0.6, 0.6, line=CYAN, line_w=1.25)
            pill(s, x - 0.45, y - 0.85, "we are here", fill=CYAN, color=NAVY, size=7.5, w=0.95)
        text(s, x - 0.2, y + 0.3, 1.9, 0.3, name, size=12, bold=True, color=WHITE if now else MUTED_D)
        text(s, x - 0.2, y + 0.6, 1.9, 0.6, desc, size=9.5, color=MUTED_D, line_spacing=1.15)
        x += 3.7
    footer(s, "Traction", "Prototype status", 16, dark=True)
    notes(s, """
No revenue yet — say it plainly — but the whole stack exists: data and trained models, an inference service, a live dashboard, a cloud broker, and firmware for the complete sensor stack including the safety workflow.
That de-risks the next step: the pilot is an integration and validation exercise, not an invention exercise.
Firmware verification is host-side so far (compiles against the real libraries; 87 behavioural checks). On-body validation and battery-life measurements come from the bench phase starting now.""")
    register(16, "Traction", """
Dark canvas. Four KPI tiles (2.85 × 2.35 in, navy-2 with coloured top bars): 34 pt figure, tracked unit label, 10 pt detail. Below: a horizontal maturity timeline (Concept → Prototype → Pilot → Launch) with a highlighted cyan "WE ARE HERE" node on Prototype. Footer "TRACTION | PROTOTYPE STATUS".""",
             "see notes", ["4 KPI tiles", "Maturity timeline"])


def slide_market(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "Start with independent aging in Egypt,\nexpand across MENA", w=9.5)
    segs = [
        ("First wedge", "Independent aging", "Older adults living at home who benefit from fall detection and proactive monitoring.",
         f"{FACTS['eg_60plus']} Egyptians aged 60+ ({FACTS['eg_60plus_pct']}) — CAPMAS 2024", VIOLET),
        ("The buyer", "Family & caregivers", "Adult children who want alerts, location context and peace of mind while at work.",
         "Household decision-maker; subscription payer", INDIGO),
        ("Expansion", "Wellness & stress", "Professionals who want context on stress, sleep and recovery — not another raw score.",
         "Same band, different app mode", "0F9F6E"),
    ]
    cw, gap = 3.85, 0.29
    x = MARGIN
    for tag, head, body, stat, col in segs:
        rect(s, x, 2.3, cw, 3.1, fill=WHITE, line=LIGHT_3, radius=0.18)
        pill(s, x + 0.3, 2.55, tag, fill=col, size=8)
        text(s, x + 0.3, 3.05, cw - 0.6, 0.5, head, size=18, bold=True, color=INK, font=FONT_HEAD)
        text(s, x + 0.3, 3.6, cw - 0.6, 1.0, body, size=11, color=SLATE, line_spacing=1.2)
        hline(s, x + 0.3, 4.65, cw - 0.6)
        text(s, x + 0.3, 4.78, cw - 0.6, 0.5, stat, size=10, bold=True, color=col, line_spacing=1.15)
        x += cw + gap
    # global context strip
    rect(s, MARGIN, 5.75, SLIDE_W - 2 * MARGIN, 0.95, fill=NAVY, radius=0.14)
    strip = [(FACTS["who_deaths"], "fatal falls per year worldwide (WHO)"),
             (FACTS["who_medical"], "falls a year need medical attention (WHO)"),
             (FACTS["who_lmic"], "of fall deaths are in low- and middle-income countries")]
    x = MARGIN + 0.35
    for big, small in strip:
        text(s, x, 5.85, 1.5, 0.75, big, size=22, bold=True, color=WHITE, font=FONT_HEAD, anchor="m")
        text(s, x + 1.5, 5.85, 2.3, 0.75, small, size=9.5, color=MUTED_D, anchor="m", line_spacing=1.15)
        x += 4.0
    footer(s, "Market", "Entry wedge and expansion", 17)
    notes(s, """
Focus wins: the first commercial wedge is independent aging in Egypt — 9.3 million people over 60 (8.8 % of the population, CAPMAS 2024), most living at home, with adult children who work.
The buyer and the wearer are different people; pricing, onboarding and the app are designed for the buyer, the band for the wearer.
Global context: WHO estimates 684 000 fatal falls a year and 37.3 million falls needing medical attention; over 80 % of fall deaths happen in low- and middle-income countries — exactly the markets premium smartwatches under-serve.
TAM/SAM/SOM in currency terms is deliberately left for the appendix until pilot data supports a defensible price point.""")
    register(17, "Market", """
Light canvas. Three white rounded segment cards (3.85 × 3.1 in) each with a coloured tag pill (FIRST WEDGE / THE BUYER / EXPANSION), an 18 pt segment name, 11 pt description and a coloured key fact under a hairline. Bottom: navy strip with three 22 pt WHO statistics and 9.5 pt captions. Footer "MARKET | ENTRY WEDGE AND EXPANSION".""",
             "see notes", ["3 segment cards", "WHO statistics strip"])


def slide_business(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "Commercial model", sub="Hypotheses for a prototype-stage company — pricing and unit economics are validated in the pilot.")
    label(s, MARGIN, 2.25, 4, "Revenue streams", color=VIOLET, size=10)
    streams = [
        ("1", "Device sale", "One-time revenue from the band and charger; target hardware margin ≥ 35 % at volume.", VIOLET),
        ("2", "Family subscription", "Monthly access to AI insights, longer history, multi-caregiver alerts and emergency dispatch.", INDIGO),
        ("3", "B2B / B2B2C", "Pilots with senior-care providers, insurers, employers and remote-care partners; per-seat pricing.", "0F9F6E"),
    ]
    y = 2.7
    for num, head, body, col in streams:
        disc(s, MARGIN + 0.22, y + 0.22, 0.42, col, num, size=11)
        text(s, MARGIN + 0.75, y - 0.02, 2.6, 0.4, head, size=14, bold=True, color=INK)
        text(s, MARGIN + 0.75, y + 0.35, 5.2, 0.8, body, size=10.5, color=SLATE, line_spacing=1.2)
        y += 1.15
    vline(s, 7.1, 2.3, 3.9)
    label(s, 7.5, 2.25, 5, "Unit economics — working assumptions", color=VIOLET, size=10)
    rows = [
        ("Line", "Prototype", "Volume target"),
        ("Bill of materials", "≈ US$ 45–60 (modules)", "< US$ 30 (custom PCB, 5k units)"),
        ("Device price", "—", "US$ 79–99 equivalent, local pricing"),
        ("Subscription", "—", "US$ 3–6 / month per household"),
        ("Gross margin", "n/a", "≥ 60 % blended after year 1"),
    ]
    table(s, 7.5, 2.7, [1.45, 1.55, 2.2], rows, header_fill=NAVY, row_h=0.46, head_h=0.4, size=9.5)
    text(s, 7.5, 5.35, 5.2, 0.7, "Assumptions to validate: willingness to pay in EGP, churn after the first alert, and B2B2C reimbursement partners.",
         size=9.5, color=SLATE, italic=True, line_spacing=1.2)
    footer(s, "Business", "Commercial model", 18)
    notes(s, """
Three streams, in order of maturity: a device sale to get the band on the wrist, a family subscription that carries the recurring value (insight, history, escalation), and B2B2C channels where an insurer or care provider pays per seat.
Unit economics are hypotheses: the prototype BOM with off-the-shelf modules is roughly 45–60 dollars; a custom PCB at a few thousand units should bring it under 30. Price points are stated in dollar equivalents but will be set in EGP after the pilot's willingness-to-pay interviews.
Do not defend the numbers — defend the method: the pilot is designed to replace every assumption on this slide with measured data.""")
    register(18, "Business model", """
Light canvas, two columns divided by a hairline. Left: "REVENUE STREAMS" label and three numbered rows (violet / indigo / green discs, 14 pt name, 10.5 pt description). Right: "UNIT ECONOMICS — WORKING ASSUMPTIONS" label, a 3-column navy-header table (BOM, device price, subscription, gross margin) and an italic assumptions line. Footer "BUSINESS | COMMERCIAL MODEL".""",
             "see notes", ["3 revenue streams", "Unit-economics table", "Assumptions caveat"])


def slide_competition(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    title(s, "Positioned between fitness bands\nand medical alert pendants", dark=True, w=9)
    cols = ["Capability", "Fitness bands", "Premium smartwatches", "Medical alert pendants", "NeuroLink Wear"]
    rows = [
        ("Continuous multi-signal vitals (HR, SpO₂, HRV, temp, GSR)", 1, 2, 0, 2),
        ("Predictive anomaly detection (stress, fever, fatigue)", 0, 1, 0, 2),
        ("On-device fall verification + wearer prompt", 0, 2, 1, 2),
        ("Caregiver escalation with vitals and GPS link", 0, 1, 2, 2),
        ("Explains the signal in plain language", 0, 0, 0, 2),
        ("Affordable for LMIC families, no smartphone needed to wear", 2, 0, 1, 2),
    ]
    cw = [4.9, 1.75, 1.75, 1.75, 1.95]
    x0, y0, hh, rh = MARGIN, 2.25, 0.5, 0.58
    rect(s, x0, y0, sum(cw), hh, fill=NAVY_2, radius=0.08)
    rect(s, x0 + sum(cw[:4]), y0, cw[4], hh + rh * len(rows), fill=VIOLET, alpha=0.18, radius=0.08)
    x = x0
    for j, c in enumerate(cols):
        text(s, x + 0.15, y0, cw[j] - 0.2, hh, c.upper(), size=8.5, bold=True, color=CYAN if j == 4 else MUTED_D,
             spacing=1.1, anchor="m", align="l" if j == 0 else "c")
        x += cw[j]
    y = y0 + hh
    for label_, *marks in rows:
        text(s, x0 + 0.15, y, cw[0] - 0.3, rh, label_, size=10.5, color=WHITE, anchor="m", line_spacing=1.05)
        x = x0 + cw[0]
        for j, m in enumerate(marks):
            cx, cy = x + cw[j + 1] / 2, y + rh / 2
            if m == 2:
                disc(s, cx, cy, 0.2, CYAN if j == 3 else MUTED_D)
            elif m == 1:
                oval(s, cx - 0.1, cy - 0.1, 0.2, 0.2, line=MUTED_D, line_w=1.25)
            else:
                rect(s, cx - 0.08, cy - 0.015, 0.16, 0.03, fill=NAVY_3)
            x += cw[j + 1]
        hline(s, x0, y + rh, sum(cw), color=NAVY_3)
        y += rh
    # legend
    ly = y + 0.3
    disc(s, x0 + 0.1, ly, 0.16, MUTED_D); text(s, x0 + 0.25, ly - 0.12, 1.2, 0.25, "Full", size=9, color=MUTED_D)
    oval(s, x0 + 1.1, ly - 0.08, 0.16, 0.16, line=MUTED_D, line_w=1.25); text(s, x0 + 1.35, ly - 0.12, 1.2, 0.25, "Partial", size=9, color=MUTED_D)
    rect(s, x0 + 2.35, ly - 0.015, 0.14, 0.03, fill=NAVY_3); text(s, x0 + 2.6, ly - 0.12, 1.2, 0.25, "None", size=9, color=MUTED_D)
    text(s, 7.0, ly - 0.15, 5.7, 0.4, "Premium watches do parts of this at 5–10× the price and assume a paired smartphone; pendants react but never predict.",
         size=9.5, color=MUTED_D, italic=True, align="r", line_spacing=1.15)
    footer(s, "Positioning", "Why we win", 19, dark=True)
    notes(s, """
Fitness bands are cheap but blind to safety; premium smartwatches have fall detection but cost several hundred dollars, assume a paired smartphone on the wearer, and are not designed around a caregiver; medical alert pendants react to a button press but never predict anything.
We sit in the gap: continuous multi-signal vitals, prediction, on-device fall verification and caregiver escalation — at a price a family in Cairo can pay, and without the wearer needing a smartphone.
Keep competitor claims general and fair; if asked about a specific brand, compare on price, caregiver features and phone dependence.""")
    register(19, "Competitive positioning", """
Dark canvas. A capability matrix: 4.9 in capability column + four 1.75–1.95 in competitor columns; the NeuroLink column has a translucent violet highlight. Marks are shapes: filled disc = full (cyan in our column), ring = partial, short dash = none. Legend bottom-left, italic takeaway bottom-right. Footer "POSITIONING | WHY WE WIN".""",
             "see notes", ["Capability matrix 6 × 4", "Legend", "Takeaway line"])


def slide_roadmap(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, LIGHT)
    title(s, "Validation roadmap", sub="From a working prototype to a validated safety product in 18 months.")
    phases = [
        ("01", "Bench & on-body", "Q4 2026", ["Sensor accuracy vs. reference devices", "Fall thresholds on 20+ scripted falls", "Battery life, strap & enclosure v1"], CYAN),
        ("02", "Controlled pilot", "H1 2027", ["30–50 households in Giza & Cairo", "Detection reliability, false-alarm rate", "Caregiver app, willingness to pay"], VIOLET),
        ("03", "Safety & compliance", "H2 2027", ["Escalation SOPs, consent, privacy", "Regulatory pathway assessment", "Custom PCB, DFM, supplier quotes"], INDIGO),
        ("04", "Scale", "2028", ["Egypt launch with care partners", "B2B2C insurer / employer pilots", "GCC & MENA expansion"], "0F9F6E"),
    ]
    cw, gap, y0 = 2.85, 0.24, 2.9
    x = MARGIN
    hline(s, MARGIN + 0.4, 2.45, 11.3, color=LIGHT_3, weight=2)
    for num, head, when, items, col in phases:
        disc(s, x + 0.4, 2.45, 0.34, col, num, size=9, txt_color=NAVY if col == CYAN else WHITE)
        rect(s, x, y0, cw, 3.3, fill=WHITE, line=LIGHT_3, radius=0.16)
        text(s, x + 0.3, y0 + 0.25, cw - 0.5, 0.4, head, size=15, bold=True, color=INK)
        label(s, x + 0.3, y0 + 0.65, cw - 0.5, when, color=col if col != CYAN else "0891B2", size=9)
        text(s, x + 0.3, y0 + 1.1, cw - 0.55, 2.0, [{"text": "–  " + t, "space_after": 6} for t in items], size=11, color=SLATE, line_spacing=1.15)
        x += cw + gap
    text(s, MARGIN, 6.4, 12, 0.4, "Key risks we track: clinical validity of wrist PPG · false-alarm fatigue · battery life with GPS · data privacy and consent · hardware supply.",
         size=9.5, color=SLATE, italic=True)
    footer(s, "Roadmap", "Validation path", 20)
    notes(s, """
Four phases, each with a measurable exit: bench accuracy against reference devices; a 30–50 household pilot measuring detection reliability, false-alarm rate and willingness to pay; a safety and compliance phase that turns the workflow into SOPs and assesses the regulatory pathway; then scale with care partners in Egypt and B2B2C pilots.
Name the risks before investors do: wrist PPG accuracy, alarm fatigue, battery life with GPS, privacy and consent, supply chain. Each has an owner and a test in the plan.""")
    register(20, "Roadmap", """
Light canvas. A horizontal timeline with four numbered coloured nodes over four white phase cards (2.85 × 3.3 in): 15 pt phase name, tracked date label, three dash-bullets at 10.5 pt. Italic key-risk line at the bottom. Footer "ROADMAP | VALIDATION PATH".""",
             "see notes", ["Timeline + 4 phase cards", "Risk line"])


def slide_team(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    title(s, "Team", dark=True, sub="Five seats across embedded systems, data science, product and care — advisors marked as recruiting.")
    members = [
        ("DS", "Diaa Salah", "CEO · Product & embedded systems", "Firmware, sensor integration, system architecture.", VIOLET),
        ("ML", "[Co-founder name]", "CTO · AI & data", "Anomaly models, pipeline, cloud services and dashboard.", INDIGO),
        ("TM", "[Team member 3]", "[Role / specialty]", "Add their contribution or one shipped proof point.", "8B5CF6"),
        ("CA", "[Clinical advisor]", "Geriatrics / family medicine — recruiting", "Protocol design, clinical validity, pilot ethics.", CYAN),
        ("GP", "[Growth lead]", "Partnerships & go-to-market — recruiting", "Senior-care providers, insurers, distribution.", MINT),
    ]
    cw, gap = 2.34, 0.18
    x = 0.55
    for ini, name, role, body, col in members:
        rect(s, x, 2.3, cw, 3.62, fill=NAVY_2, radius=0.16)
        disc(s, x + cw / 2, 3.02, 0.76, col, ini, size=13, txt_color=NAVY if col in (CYAN, MINT) else WHITE)
        text(s, x + 0.18, 3.52, cw - 0.36, 0.48, name, size=11.4, bold=True, color=WHITE, line_spacing=1.0)
        text(s, x + 0.18, 4.02, cw - 0.36, 0.63, role, size=8.8, bold=True, color=col, line_spacing=1.08)
        text(s, x + 0.18, 4.72, cw - 0.36, 0.98, body, size=8.8, color=MUTED_D, line_spacing=1.13)
        x += cw + gap
    text(s, MARGIN, 6.2, 12, 0.4, "Customize card 3 with the fifth teammate’s name, photo and one proof point.",
         size=9.5, color=MUTED_D, italic=True)
    footer(s, "Team", "Who is building it", 21, dark=True)
    notes(s, """
The layout now accommodates five people. Replace card 3’s placeholder with the additional teammate’s name, role, photo and one shipped proof point. Keep the clinical advisor and growth lead clearly marked as recruiting until those seats are filled.
One proof point per person — what each has shipped or published — beats a list of titles. Highlight the complementary split: embedded/product, AI/data, and the fifth teammate’s actual specialty.
State the open advisor/partnership seats honestly and explain how the pilot plan will fill them.""")
    register(21, "Team", """
Dark canvas. Five evenly spaced navy-2 cards (2.34 × 3.62 in) across the slide, each with a 0.76 in colored initials disc, compact name, role and contribution text. Two roles remain marked recruiting; card 3 is an editable placeholder for the fifth teammate. Footer "TEAM | WHO IS BUILDING IT".""",
             "see notes", ["5 member cards", "Card 3 placeholder for fifth teammate", "Recruiting labels on open roles"])


def slide_ask(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, NAVY)
    picture(s, "hero", 6.6, 0, SLIDE_W - 6.6, SLIDE_H, focus=(0.65, 0.5), placeholder_label="hero render")
    g = rect(s, 6.6, 0, 3.0, SLIDE_H, fill=NAVY)
    gradient(g, [(0, NAVY, 1.0), (1, NAVY, 0.0)], angle=0)
    rect(s, 0, 0, 6.61, SLIDE_H, fill=NAVY)
    glow(s, 0.3, 7.4, 1.2, VIOLET, 0.18)
    rect(s, MARGIN, 0.85, 0.55, 0.07, fill=CYAN)
    text(s, MARGIN, 1.15, 6.3, 1.5, "Help us close the gap between\na reading and a response.", size=28, bold=True, color=WHITE, font=FONT_HEAD, line_spacing=1.05)
    label(s, MARGIN, 2.85, 4, "The ask", color=CYAN, size=10)
    asks = [
        ("Pilot partners", "Senior-care providers, clinics and insurers in Egypt for a 30–50 household pilot."),
        ("Clinical validation support", "A geriatrics advisor and access to reference devices for accuracy studies."),
        ("Pre-seed funding", "[US$ ___ k] for 18 months — bench validation, pilot, custom PCB and the mobile app."),
    ]
    y = 3.2
    for head, body in asks:
        rect(s, MARGIN, y + 0.07, 0.08, 0.5, fill=VIOLET, radius=0.04)
        text(s, MARGIN + 0.3, y, 5.7, 0.35, head, size=13.5, bold=True, color=WHITE)
        text(s, MARGIN + 0.3, y + 0.33, 5.7, 0.6, body, size=10.5, color=MUTED_D, line_spacing=1.2)
        y += 0.85
    # indicative use of funds
    label(s, MARGIN, 5.72, 4, "Indicative use of funds", color=MUTED_D, size=8.5)
    parts = [("Hardware & compliance", 0.40, VIOLET), ("Pilot & validation", 0.35, CYAN), ("Team & app", 0.25, MINT)]
    x, total_w = MARGIN, 5.9
    for name, share, col in parts:
        w = total_w * share
        rect(s, x, 6.02, w - 0.04, 0.16, fill=col, radius=0.05)
        text(s, x, 6.22, w, 0.3, f"{int(share * 100)}%  {name}", size=8.5, color=MUTED_D)
        x += w
    text(s, MARGIN, 6.6, 6.2, 0.3, "[founder@neurolinkwear.example]  ·  [+20 1xx xxx xxxx]  ·  github.com/DiaaSalah57/Neuro-Link-Wear_SmartBand", size=8.5, color=MUTED_D)
    footer(s, "Next step", "Pilot, validation, funding", 22, dark=True)
    notes(s, """
Close on the mission line, then be concrete: three asks — pilot partners, clinical validation support, and a pre-seed round sized for 18 months (fill in the amount before presenting).
Use of funds is indicative: roughly 40 % hardware and compliance, 35 % pilot and validation, 25 % team and app.
End with the next step you want from this room: an introduction to a care provider, a pilot site, or a follow-up meeting on the round.""")
    register(22, "The ask / closing", """
Dark canvas mirroring the cover: hero render on the right 50% fading into navy. Left: cyan accent bar, 30 pt two-line mission headline, "THE ASK" label with three items (violet bar, 13.5 pt heading, 10.5 pt detail), an indicative use-of-funds bar (40 / 35 / 25) and a contact line with placeholders. Footer "NEXT STEP | PILOT, VALIDATION, FUNDING".""",
             "see notes", ["Mission headline", "3 asks", "Use-of-funds bar", "Contact placeholders"])


# ──────────────────────────────────────────────────────────────────────────────
# 5. BUILD + COMPANION DOCUMENT
# ──────────────────────────────────────────────────────────────────────────────
SLIDES = [slide_cover, slide_problem, slide_solution, slide_hardware, slide_architecture, slide_edge,
          slide_ai, slide_ai_architecture, slide_model_roles, slide_model_results, slide_equation_library,
          slide_personal_calibration, slide_detection_tiers, slide_safety, slide_app, slide_traction,
          slide_market, slide_business, slide_competition, slide_roadmap, slide_team, slide_ask]


def build(out_path: str, specs_path: str | None):
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    for fn in SLIDES:
        fn(prs)
    prs.save(out_path)
    if specs_path:
        write_specs(specs_path, out_path)


def write_specs(path: str, deck_name: str):
    lines = [
        "# NeuroLink Wear — pitch deck: layout specs & speaker notes",
        "",
        f"Generated by `build_deck.py` → `{os.path.basename(deck_name)}` (22 slides, 16:9, 13.333 × 7.5 in).",
        "",
        "## Design system",
        "",
        "| Token | Value | Use |",
        "|---|---|---|",
        f"| Navy | `#{NAVY}` | dark canvases, stat cards |",
        f"| Navy-2 / Navy-3 | `#{NAVY_2}` / `#{NAVY_3}` | cards and dividers on dark |",
        f"| Violet | `#{VIOLET}` | primary accent, headers, numerals |",
        f"| Indigo | `#{INDIGO}` | secondary accent |",
        f"| Cyan | `#{CYAN}` | highlights on dark, 'now' markers |",
        f"| Mint / Amber / Pink | `#{MINT}` / `#{AMBER}` / `#{PINK}` | success / warning / emergency |",
        f"| Light / Ink / Slate | `#{LIGHT}` / `#{INK}` / `#{SLATE}` | light canvases and text |",
        f"| Fonts | {FONT_HEAD} (headings) · {FONT_BODY} (body) | change `FONT_HEAD` / `FONT_BODY` at the top of the script |",
        "",
        "Rhythm: dark and light canvases alternate; every content slide carries a 32 pt headline, an optional 14 pt sub-line, "
        "a bottom-left tracked section tag (`SECTION | TAGLINE`) and a top-right slide number. Photos are rounded (0.2 in) "
        "or full-bleed with a navy gradient fade. Numbers and labels use tracked uppercase 8–10 pt captions.",
        "",
        "## Slides",
        "",
    ]
    for sp in SPECS:
        lines += [f"### {sp.n:02d} · {sp.title}", "", "**Layout**", "", sp.layout, ""]
        if sp.elements:
            lines += ["**Key elements**", ""] + [f"- {e}" for e in sp.elements] + [""]
        if sp.notes != "n/a":
            lines += ["**Speaker notes**", ""]
        lines += [""]
    # attach the real notes text from the deck (single source of truth)
    prs = Presentation(deck_name)
    out = []
    for sp, slide in zip(SPECS, prs.slides):
        block = [f"### {sp.n:02d} · {sp.title}", "", "**Layout**", "", sp.layout, ""]
        if sp.elements:
            block += ["**Key elements**", ""] + [f"- {e}" for e in sp.elements] + [""]
        nt = slide.notes_slide.notes_text_frame.text.strip()
        if nt:
            block += ["**Speaker notes**", ""] + [f"> {ln}" if ln else ">" for ln in nt.splitlines()] + [""]
        out += block
    head = lines[: lines.index("## Slides") + 2]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(head + out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the NeuroLink Wear pitch deck")
    ap.add_argument("--out", default="NeuroLink_Wear_Pitch_Deck.pptx")
    ap.add_argument("--specs", default="SLIDE_SPECS_AND_NOTES.md", help="companion markdown ('' to skip)")
    a = ap.parse_args()
    build(a.out, a.specs or None)
    print(f"wrote {a.out}" + (f" and {a.specs}" if a.specs else ""))

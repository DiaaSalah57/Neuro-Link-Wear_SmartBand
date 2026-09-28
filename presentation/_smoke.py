"""
Section render harness — build only selected sections into a scratch deck, e.g.

    python3 presentation/_smoke.py sec_c_intel
    python3 presentation/preview.py /tmp/smoke.pptx /tmp/prev

Used while iterating on individual slides; the full deck is built by build.py.
"""
import sys, importlib
sys.path.insert(0, '.')
from pptx import Presentation
import kit


class B:
    def __init__(self, prs):
        self.prs = prs
        self.n = 0

    def num(self):
        self.n += 1
        return self.n

    def divider(self, number, title, subtitle, items=None, **kw):
        self.n += 1
        return kit.divider(self.prs, int(number), title, subtitle, items, **kw)


mods = sys.argv[1:] or ['sec_a1_open']
prs = Presentation()
prs.slide_width = kit.Inches(kit.W)
prs.slide_height = kit.Inches(kit.H)
b = B(prs)
for m in mods:
    importlib.import_module(m).build(b)
prs.save('/tmp/smoke.pptx')
print('slides', len(prs.slides))

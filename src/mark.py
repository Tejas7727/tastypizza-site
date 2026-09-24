"""The modernised Tasty Pizza mark.

The old logo is cartoon clip-art: a stock chef and a Cooper Black italic wordmark.
It reads as 1998 and it cannot be printed in one colour, scaled to a favicon, or
animated. This replaces it inside the poster direction while the original stays
untouched on the current site.

Two parts, usable together or apart:

  emblem    a disc with a slice notched out of it. Three concentric bands so it
            reads as a pizza up close and as a printer's registration dot at
            16px. Works in one ink, so it can be embroidered, stamped on a box,
            or cut in vinyl on the window.

  wordmark  TASTY over PIZZA, heavy and tight, with the second word printed a
            hair out of register in the warm ink. The misregistration is the
            whole design language of the site, stated once in the logo.
"""


import math


def _wedge(cx, cy, r, a0, a1, fill):
    """One slice of the disc, as a filled sector."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return (f'<path d="M{cx} {cy} L{x0:.2f} {y0:.2f} '
            f'A{r} {r} 0 {large} 1 {x1:.2f} {y1:.2f} Z" fill="{fill}"/>')


def emblem(size=64, pulled=True, one_ink=False):
    """A pizza cut into six, which is also a colour wheel.

    Earlier versions put pepperoni dots inside a ring and every one of them read
    as a face — two eyes and a mouth, unavoidably. Segments solve that: the shape
    says 'cut pizza' and 'colour wheel' at once, which is exactly what this site
    is about, and it survives being printed in a single ink.
    """
    cx = cy = 32
    r = 29
    ink, accent, pop = "var(--ink)", "var(--accent)", "var(--pop)"
    if one_ink:
        accent, pop = ink, "var(--paper)"

    # six slices, alternating warm inks; one is nudged out of the pie
    slices = []
    for i in range(6):
        a0, a1 = -90 + i * 60, -90 + (i + 1) * 60
        fill = accent if i % 2 == 0 else pop
        if pulled and i == 1:
            continue
        slices.append(_wedge(cx, cy, r, a0, a1, fill))

    out = "".join(slices)
    if pulled:
        # the loose slice, lifted clear on its own angle
        dx = 7.5 * math.cos(math.radians(-30))
        dy = 7.5 * math.sin(math.radians(-30))
        out += (f'<g transform="translate({dx:.2f} {dy:.2f})">'
                + _wedge(cx, cy, r, -30, 30, pop) + "</g>")

    return (
        f'<svg class="emblem" width="{size}" height="{size}" viewBox="0 0 64 64" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Tasty Pizza">'
        f'<circle cx="{cx}" cy="{cy}" r="{r + 2}" fill="{ink}" opacity="{0 if one_ink else .1}"/>'
        f'{out}'
        f'<circle cx="{cx}" cy="{cy}" r="4.2" fill="{ink}"/>'
        f'</svg>'
    )


def wordmark(cls=""):
    """Two stacked words. PIZZA sits 3px off register in the warm ink — the
    signature of the whole design, said once, in the name."""
    return (
        f'<span class="wordmark {cls}" role="img" aria-label="Tasty Pizza">'
        f'<span class="wm-1">Tasty</span>'
        f'<span class="wm-2" aria-hidden="true">Pizza</span>'
        f'</span>'
    )


def lockup(size=44, stacked=False):
    """Emblem + wordmark, the version that goes in the masthead."""
    return (f'<span class="lockup{" is-stacked" if stacked else ""}">'
            f'{emblem(size)}{wordmark()}</span>')

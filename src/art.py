"""Drawn artwork for the poster design.

Everything here is flat vector in four inks, and every fill is a CSS variable, so
one drawing works in every palette and recolours itself when the page cross-fades
between sections.

Each illustration is split into named PLATES the way a screen print is — one pass
per ink. The page animates the plates into register, which is where the motion in
this design comes from, so the split is structural and not decoration.

    plate 0  paper furniture   background shapes, the stage
    plate 1  ink (cool)        ground, type, leaves, shadow shapes
    plate 2  accent (warm)     the food's body
    plate 3  pop (warm)        cheese, highlights, small marks
"""


def _plate(n, body, dx=0, dy=0, rot=0):
    """One ink pass. data-plate drives the registration animation."""
    return (f'<g class="plate" data-plate="{n}" '
            f'style="--dx:{dx}px;--dy:{dy}px;--rot:{rot}deg">{body}</g>')


# ---------------------------------------------------------------- furniture

def halftone(seed=0):
    """A dot screen, the texture a real press leaves. Drawn once, reused by <use>."""
    return (
        '<defs><pattern id="halftone" width="7" height="7" patternUnits="userSpaceOnUse">'
        '<circle cx="1.6" cy="1.6" r="1.05" fill="var(--ink)" opacity=".16"/>'
        '</pattern>'
        '<pattern id="halftone-fine" width="5" height="5" patternUnits="userSpaceOnUse">'
        '<circle cx="1.2" cy="1.2" r=".72" fill="var(--ink)" opacity=".12"/>'
        '</pattern></defs>'
    )


def corner_arc(x, y, r, fill="var(--ink)", rot=0):
    return (f'<path d="M{x} {y} h{r} a{r} {r} 0 0 1 -{r} {r} Z" fill="{fill}" '
            f'transform="rotate({rot} {x} {y})"/>')


def bars(x, y, w, n=4, gap=6, thick=5, fill="var(--ink)", vertical=False):
    out = []
    for i in range(n):
        if vertical:
            out.append(f'<rect x="{x + i * (thick + gap)}" y="{y}" width="{thick}" height="{w}" fill="{fill}"/>')
        else:
            out.append(f'<rect x="{x}" y="{y + i * (thick + gap)}" width="{w}" height="{thick}" fill="{fill}"/>')
    return "".join(out)


def dot(cx, cy, r, fill="var(--ink)"):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'


# ---------------------------------------------------------------- the pizza

def pizza(cx=176, cy=236, r=132):
    """Top-down, one slice lifted clear with the cheese still stretching after it.
    Warm inks only on the pie; the cool ink stays furniture. A cool-inked pizza
    stops reading as food, which the duotone study proved the hard way."""
    cheese = r * 0.84

    pep = [(-0.46, -0.40, 1.00), (0.10, -0.54, 0.86), (0.48, -0.16, 0.92),
           (-0.10, -0.06, 1.06), (-0.54, 0.18, 0.84), (0.26, 0.40, 0.96),
           (-0.26, 0.50, 0.88)]
    pepperoni = "".join(
        f'<circle cx="{cx + dx * cheese * 0.8:.1f}" cy="{cy + dy * cheese * 0.8:.1f}" '
        f'r="{15 * s:.1f}" fill="var(--accent)"/>'
        f'<circle cx="{cx + dx * cheese * 0.8 - 2.5:.1f}" cy="{cy + dy * cheese * 0.8 - 2.5:.1f}" '
        f'r="{15 * s * 0.42:.1f}" fill="var(--pop)" opacity=".34"/>'
        for dx, dy, s in pep)

    # bubbles of browned cheese, so the field is not a flat disc
    bubbles = "".join(
        f'<circle cx="{cx + bx}" cy="{cy + by}" r="{br}" fill="var(--accent)" opacity=".2"/>'
        for bx, by, br in [(-30, -78, 9), (72, 46, 7), (-84, 52, 6), (34, -22, 5)])

    # the lifted slice, up and to the right, with two strands of cheese still on it
    wedge = (
        f'<g transform="translate({cx + 156} {cy - 150}) rotate(-15)">'
        f'<path d="M0 0 L150 -49 A158 158 0 0 1 150 49 Z" fill="var(--accent)"/>'
        f'<path d="M11 0 L139 -44 A147 147 0 0 1 139 44 Z" fill="var(--pop)"/>'
        f'<circle cx="74" cy="-13" r="13" fill="var(--accent)"/>'
        f'<circle cx="104" cy="17" r="11" fill="var(--accent)"/>'
        f'<circle cx="46" cy="14" r="9" fill="var(--accent)"/>'
        f'<path d="M150 -49 A158 158 0 0 1 150 49" stroke="var(--accent)" '
        f'stroke-width="17" fill="none" stroke-linecap="round"/>'
        f'</g>'
        # cheese pull back toward the pie
        f'<path d="M{cx + 150} {cy - 108} q -34 44 -58 96" stroke="var(--pop)" stroke-width="7" '
        f'fill="none" stroke-linecap="round" opacity=".92"/>'
        f'<path d="M{cx + 168} {cy - 92} q -30 50 -44 104" stroke="var(--pop)" stroke-width="5" '
        f'fill="none" stroke-linecap="round" opacity=".7"/>'
    )

    return (
        _plate(1,
               f'{corner_arc(cx - 196, cy - 206, 92)}'
               f'{dot(cx + 178, cy + 150, 21)}'
               f'{bars(cx - 208, cy + 154, 92, n=3, gap=9, thick=7)}'
               f'<circle cx="{cx}" cy="{cy}" r="{r + 16:.0f}" fill="var(--ink)" opacity=".12"/>',
               dx=-10, dy=7, rot=-1.5)
        + _plate(2,
                 f'<circle cx="{cx}" cy="{cy}" r="{r:.0f}" fill="var(--accent)"/>{wedge}',
                 dx=8, dy=-6, rot=1.2)
        + _plate(3,
                 f'<circle cx="{cx}" cy="{cy}" r="{cheese:.0f}" fill="var(--pop)"/>'
                 f'{bubbles}{pepperoni}',
                 dx=-5, dy=10, rot=-0.7)
    )


# ---------------------------------------------------------------- the donair

def donair(cx=232, cy=222):
    """The cone on the vertical spit, mid-shave, with the knife alongside.
    Halifax's official food deserves to be the thing you actually see."""
    # shaved bands down the cone, narrow at the top and wide at the base
    bands = ""
    for i in range(9):
        t = i / 8
        half = 34 + t * 86
        y = cy - 146 + i * 34
        bands += (f'<path d="M{cx - half:.0f} {y} q {half:.0f} {14 + i * 1.6:.0f} {half * 2:.0f} 0" '
                  f'stroke="var(--pop)" stroke-width="{6 + t * 3:.1f}" fill="none" '
                  f'stroke-linecap="round" opacity="{0.92 - i * 0.045:.2f}"/>')

    # a few shavings falling away from the blade
    shavings = "".join(
        f'<path d="M{cx + 128 + dx} {cy + dy} q 22 6 38 -4" stroke="var(--pop)" '
        f'stroke-width="6" fill="none" stroke-linecap="round" opacity="{o}"/>'
        for dx, dy, o in [(4, -52, ".85"), (14, -6, ".6"), (0, 40, ".45")])

    return (
        _plate(1,
               f'{corner_arc(cx - 188, cy - 200, 88)}'
               f'{dot(cx + 176, cy + 160, 20)}'
               f'{bars(cx + 104, cy - 198, 76, n=4, gap=8, thick=6, vertical=True)}'
               # the spit: rod through the whole cone, plus the base plate
               f'<rect x="{cx - 7}" y="{cy - 202}" width="14" height="392" rx="7" fill="var(--ink)"/>'
               f'<rect x="{cx - 104}" y="{cy + 176}" width="208" height="18" rx="9" fill="var(--ink)"/>'
               # the knife
               f'<g transform="rotate(-9 {cx + 150} {cy})">'
               f'<rect x="{cx + 142}" y="{cy - 126}" width="15" height="150" rx="4" fill="var(--ink)"/>'
               f'<rect x="{cx + 144}" y="{cy + 24}" width="11" height="58" rx="5" fill="var(--ink)" opacity=".62"/>'
               f'</g>',
               dx=-9, dy=6, rot=-1.2)
        + _plate(2,
                 # cone: narrow shoulders, heavy base — the silhouette does the work
                 f'<path d="M{cx} {cy - 176} '
                 f'c 40 28 66 84 78 158 c 8 46 10 70 6 82 '
                 f'c -30 16 -138 16 -168 0 c -4 -12 -2 -36 6 -82 '
                 f'c 12 -74 38 -130 78 -158 Z" fill="var(--accent)"/>',
                 dx=9, dy=-7, rot=1.3)
        + _plate(3, bands + shavings, dx=-5, dy=9, rot=-0.7)
    )


# ---------------------------------------------------------------- garlic fingers

def garlic_fingers(cx=196, cy=214):
    """A pan cut into fingers with one pulled loose, and the pot of donair sauce
    it is never served without. The pull is the whole point of the dish."""
    strips = "".join(
        f'<rect x="{cx - 152 + i * 45}" y="{cy - 112}" width="35" height="206" rx="10" '
        f'fill="var(--pop)"/>' for i in range(6))
    flecks = "".join(
        f'<circle cx="{cx - 140 + (i * 41) % 268}" cy="{cy - 92 + (i * 67) % 170}" r="3.6" '
        f'fill="var(--accent)" opacity=".7"/>' for i in range(20))
    # one finger lifted out and tilted, trailing cheese
    pulled = (
        f'<g transform="translate({cx + 128} {cy - 168}) rotate(24)">'
        f'<rect x="0" y="0" width="35" height="196" rx="10" fill="var(--pop)"/>'
        f'<circle cx="11" cy="42" r="3.6" fill="var(--accent)" opacity=".7"/>'
        f'<circle cx="24" cy="96" r="3.6" fill="var(--accent)" opacity=".7"/>'
        f'<circle cx="13" cy="150" r="3.6" fill="var(--accent)" opacity=".7"/>'
        f'</g>'
        f'<path d="M{cx + 146} {cy - 24} q -20 32 -46 52" stroke="var(--pop)" stroke-width="6" '
        f'fill="none" stroke-linecap="round" opacity=".8"/>'
    )
    return (
        _plate(1,
               f'{corner_arc(cx - 194, cy - 188, 84)}'
               f'{dot(cx - 168, cy + 168, 20)}'
               f'{bars(cx + 128, cy + 150, 86, n=3, gap=9, thick=7)}'
               f'<rect x="{cx - 160}" y="{cy - 124}" width="320" height="230" rx="18" '
               f'fill="var(--ink)" opacity=".13"/>',
               dx=-8, dy=7, rot=-1.1)
        + _plate(2,
                 f'<rect x="{cx - 156}" y="{cy - 120}" width="312" height="222" rx="16" fill="var(--accent)"/>'
                 f'<circle cx="{cx + 132}" cy="{cy + 150}" r="46" fill="var(--accent)"/>',
                 dx=8, dy=-6, rot=1.2)
        + _plate(3,
                 f'{strips}{flecks}{pulled}'
                 f'<circle cx="{cx + 132}" cy="{cy + 150}" r="34" fill="var(--paper)"/>'
                 f'<circle cx="{cx + 132}" cy="{cy + 150}" r="26" fill="var(--pop)" opacity=".85"/>',
                 dx=-5, dy=10, rot=-0.7)
    )


# name -> (draw fn, viewBox). Each composition needs a frame sized to it; a shared
# 400-square clipped the lifted slice and the pulled finger clean off.
ILLOS = {
    "pizza": (pizza, "0 0 520 450"),
    "donair": (donair, "0 0 470 460"),
    "garlic-fingers": (garlic_fingers, "0 0 500 450"),
}


def illo(name, cls=""):
    """One illustration, wrapped in its own frame with the press texture."""
    fn, box = ILLOS[name]
    return (f'<svg class="illo {cls}" data-illo="{name}" viewBox="{box}" '
            f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" '
            f'preserveAspectRatio="xMidYMid meet">'
            f'{halftone()}{fn()}</svg>')

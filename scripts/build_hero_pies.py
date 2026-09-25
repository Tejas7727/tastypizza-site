"""Prepare the home-page pizzas for the web.

The pies in assets/hero-in/ arrive already cut out, with a clean alpha edge.
Nothing here re-masks them — that is the artist's work and it is better than
anything this script would guess. All it does is crop square to the pixels
that are actually opaque, size them for the page, and write WebP.

    python scripts/build_hero_pies.py
    python scripts/build_hero_pies.py pepperoni      # just this one

Drop a new cut-out in assets/hero-in/ named after the slug, run this, and the
home page picks it up.
"""
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "hero-in"
OUT = ROOT / "docs" / "assets" / "img"
SIZE = 680          # the hero never draws a pie bigger than this
PAD = 0.012         # a sliver of margin so the crust edge is not shaved


def main():
    only = [a.lower() for a in sys.argv[1:]]
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SRC.iterdir()
                   if p.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg"))
    if not files:
        print(f"nothing in {SRC}")
        return 1

    for p in files:
        slug = p.stem
        if only and slug not in only:
            continue
        im = Image.open(p)
        if im.mode != "RGBA":
            print(f"  ! {slug}: no alpha channel — expected a cut-out PNG, skipped")
            continue
        box = im.getchannel("A").getbbox()
        if not box:
            print(f"  ! {slug}: fully transparent, skipped")
            continue

        # square the crop around the pie so a round thing stays round
        l, t, r, b = box
        cx, cy = (l + r) / 2, (t + b) / 2
        half = max(r - l, b - t) / 2 * (1 + PAD)
        pie = im.crop((round(cx - half), round(cy - half),
                       round(cx + half), round(cy + half)))
        # crop can run past the canvas; that lands as transparent, which is fine
        pie = pie.resize((SIZE, SIZE), Image.LANCZOS)
        out = OUT / f"pie-{slug}.webp"
        pie.save(out, "WEBP", quality=84, method=6)
        print(f"  pie-{slug}.webp   {out.stat().st_size / 1024:6.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

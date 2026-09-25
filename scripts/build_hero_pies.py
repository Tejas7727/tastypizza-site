"""Cut the home-page pizzas out of their white background.

The pies in assets/hero-in/ are shot top-down on white. On the home page they
sit on a wooden board, so a square photo with a white corner would read as a
sticker. This finds the pie, crops tight to it, and writes a WebP with a real
alpha edge so the board shows through around the crust.

    python scripts/build_hero_pies.py

Source images are whatever is in assets/hero-in/. Drop a new one in, named
after the slug, run this, and the home page picks it up.
"""
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "hero-in"
OUT = ROOT / "docs" / "assets" / "img"
SIZE = 680          # the board never draws a pie bigger than this
PAD = 0.015         # a sliver of breathing room so the crust is not shaved
WHITE = 236         # anything brighter than this on all channels is background


def alpha_from_white(im):
    """Background is near-white, the pizza is not.

    Two things this has to get right. Bright cheese highlights are as pale as
    the background, so the background is found by flooding in from the edges
    rather than by brightness alone — anything the flood cannot reach is pizza,
    highlights included. And the source has a soft grey drop shadow under the
    pie, which is not white and would survive as a pale smear on the wooden
    board; since a pizza is a circle, the mask is clipped to the circle that
    the pie's own coloured pixels describe, and the shadow falls outside it."""
    g = im.convert("L")
    flood = g.point(lambda v: 255 if v >= WHITE else 0).convert("L")
    seed = flood.copy()
    d = ImageDraw.Draw(seed)
    for xy in ((0, 0), (seed.width - 1, 0), (0, seed.height - 1),
               (seed.width - 1, seed.height - 1)):
        if seed.getpixel(xy) == 255:
            ImageDraw.floodfill(seed, xy, 128, thresh=30)
    # 128 is background the flood reached; everything else belongs to the pie
    mask = seed.point(lambda v: 0 if v == 128 else 255)

    # the circle the pie actually occupies, measured from its coloured pixels
    small = im.resize((160, 160), Image.BILINEAR)
    px = small.load()
    pts = []
    for y in range(160):
        for x in range(160):
            r, gg, b = px[x, y]
            if max(r, gg, b) - min(r, gg, b) > 26 and max(r, gg, b) > 60:
                pts.append((x, y))
    if pts:
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        rad = sorted(((p[0] - cx) ** 2 + (p[1] - cy) ** 2) ** .5 for p in pts)
        r99 = rad[int(len(rad) * .995)] * 1.035
        k = im.width / 160
        circle = Image.new("L", im.size, 0)
        ImageDraw.Draw(circle).ellipse(
            [(cx - r99) * k, (cy - r99) * k, (cx + r99) * k, (cy + r99) * k], fill=255)
        mask = ImageChops.multiply(mask, circle)

    return mask.filter(ImageFilter.GaussianBlur(1.0))


def main():
    only = [a.lower() for a in sys.argv[1:]]
    OUT.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        print(f"no {SRC}")
        return 1
    files = sorted(p for p in SRC.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    if not files:
        print(f"nothing in {SRC}")
        return 1

    for p in files:
        slug = p.stem
        if only and slug not in only:
            continue
        im = Image.open(p).convert("RGB")
        mask = alpha_from_white(im)
        box = mask.getbbox()
        if not box:
            print(f"  ! {slug}: all background, skipped")
            continue

        # square the crop around the pie so it stays round
        l, t, r, b = box
        cx, cy = (l + r) / 2, (t + b) / 2
        half = max(r - l, b - t) / 2 * (1 + PAD)
        half = min(half, cx, cy, im.width - cx, im.height - cy)
        crop = (int(cx - half), int(cy - half), int(cx + half), int(cy + half))

        rgba = im.convert("RGBA")
        rgba.putalpha(mask)
        pie = rgba.crop(crop).resize((SIZE, SIZE), Image.LANCZOS)
        out = OUT / f"pie-{slug}.webp"
        pie.save(out, "WEBP", quality=82, method=6)
        print(f"  pie-{slug}.webp   {out.stat().st_size / 1024:6.1f} KB"
              f"   (cut from {im.width}x{im.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

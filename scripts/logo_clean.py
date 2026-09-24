"""Clean up the existing Tasty Pizza logo without redrawing it.

The client's mark stays the client's mark. This only fixes the defects the file
picked up from being saved small and composited on white:

  * ~19% of its pixels are a soft semi-transparent halo, which shows as a pale
    fringe on any background that is not white
  * the edges are mushy at any size above 1x

Deliberately NOT touched: the colours. An earlier pass tried to flatten the reds
to one brand red and turned the chef's thumb into a red blotch, because skin
tones are reddish too. The artwork is the client's; only its edges get fixed.

It also cuts the chef and the wordmark into separate assets so a lockup can put
air between them, instead of shipping one raster where they overlap.

    python scripts/logo_clean.py
"""
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "research" / "current-site" / "logo.png"
OUT = ROOT / "assets" / "brand"


def harden_alpha(im, lo=46, hi=210):
    """Squeeze the alpha ramp so the halo goes and the edge stays smooth."""
    r, g, b, a = im.split()
    a = a.point(lambda v: 0 if v < lo else (255 if v > hi else int((v - lo) / (hi - lo) * 255)))
    return Image.merge("RGBA", (r, g, b, a))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    im = Image.open(SRC).convert("RGBA")

    im = harden_alpha(im)
    im = im.filter(ImageFilter.UnsharpMask(radius=0.8, percent=52, threshold=3))

    box = im.getbbox()
    im = im.crop(box)
    w, h = im.size
    print(f"cleaned: {w}x{h}")

    # full lockup, at the sizes a masthead and a share card actually need
    for scale, tag in ((1, ""), (2, "@2x"), (3, "@3x")):
        s = im.resize((w * scale, h * scale), Image.LANCZOS) if scale > 1 else im
        s.save(OUT / f"logo-clean{tag}.png")
        s.save(OUT / f"logo-clean{tag}.webp", "WEBP", quality=92, method=6, lossless=False)

    # the two halves, so a lockup can space them properly instead of overlapping
    word = im.crop((0, int(h * 0.50), w, h))
    word = word.crop(word.getbbox())
    word.save(OUT / "logo-wordmark.webp", "WEBP", quality=92, method=6)
    word.resize((word.width * 2, word.height * 2), Image.LANCZOS) \
        .save(OUT / "logo-wordmark@2x.webp", "WEBP", quality=92, method=6)

    chef = im.crop((int(w * 0.13), 0, int(w * 0.80), int(h * 0.58)))
    chef = chef.crop(chef.getbbox())
    chef.save(OUT / "logo-chef.webp", "WEBP", quality=92, method=6)
    chef.resize((chef.width * 2, chef.height * 2), Image.LANCZOS) \
        .save(OUT / "logo-chef@2x.webp", "WEBP", quality=92, method=6)

    print(f"wordmark {word.size}, chef {chef.size} -> {OUT}")

    # before / after, side by side on a mid grey so halos have nowhere to hide
    orig = Image.open(SRC).convert("RGBA")
    pad, sc = 26, 2
    sheet = Image.new("RGB", (max(orig.width, w) * sc + pad * 2,
                              (orig.height + h) * sc + pad * 3), (122, 122, 126))
    sheet.paste(orig.resize((orig.width * sc, orig.height * sc), Image.LANCZOS),
                (pad, pad), orig.resize((orig.width * sc, orig.height * sc), Image.LANCZOS))
    sheet.paste(im.resize((w * sc, h * sc), Image.LANCZOS),
                (pad, orig.height * sc + pad * 2), im.resize((w * sc, h * sc), Image.LANCZOS))
    sheet.save(ROOT / "research" / "_logo-before-after.png")
    print("wrote research/_logo-before-after.png  (top: original, bottom: cleaned)")


if __name__ == "__main__":
    main()

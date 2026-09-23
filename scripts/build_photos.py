"""Crop, grade and export the site's food photos.

Reads data/photos.json, takes the chosen candidate for each slug (or a real photo dropped
into assets/photos-in/, which always wins), applies one consistent grade so photos from
different sources sit together, and writes WebP at two widths into docs/assets/img/.

    python scripts/build_photos.py
    python scripts/build_photos.py donair poutine     # just these
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "research" / "photo-candidates"
REAL = ROOT / "assets" / "photos-in"
OUT = ROOT / "docs" / "assets" / "img"

# 4:3 card at two widths for everything; the wide 16:9 crop only for slugs that
# actually get used big, because a 1600px plate nobody sees is just page weight.
SIZES = {"": (800, 600), "@sm": (400, 300)}
WIDE = (1600, 900)
HERO_SLUGS = {"donair", "meat-lovers-pizza", "garlic-fingers", "poutine",
              "fish-and-chips", "all-dressed-pizza", "donair-pogo", "chicken-wings"}

# One grade for everything. Deliberately gentle: the copy should stay the brightest
# thing on the page, and over-saturated food photography reads as a stock library.
SATURATION = 0.96
CONTRAST = 1.07
BRIGHTNESS = 1.02
WARMTH = (1.03, 1.0, 0.975)   # r, g, b multipliers


def load_source(slug, pick):
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = REAL / f"{slug}{ext}"
        if p.exists():
            return p, True
    p = CAND / slug / f"{pick:02d}.jpg"
    return (p, False) if p.exists() else (None, False)


def crop(im, size, spec):
    # Optional pre-crop: zoom in on part of the source, e.g. to frame out a drink
    # bottle or a background face that has no business on the client's menu.
    zoom = spec.get("zoom", 1.0)
    if zoom > 1.0:
        w, h = int(im.width / zoom), int(im.height / zoom)
        cx = spec.get("fx", 0.5) * (im.width - w)
        cy = spec.get("fy", 0.5) * (im.height - h)
        im = im.crop((int(cx), int(cy), int(cx) + w, int(cy) + h))

    tw, th = size
    r = max(tw / im.width, th / im.height)
    im = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)
    left = (im.width - tw) // 2
    top = max(0, min(int((im.height - th) * spec.get("focus", 0.5)), im.height - th))
    return im.crop((left, top, left + tw, top + th))


def grade(im):
    im = ImageEnhance.Color(im).enhance(SATURATION)
    im = ImageEnhance.Contrast(im).enhance(CONTRAST)
    im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
    r, g, b = im.split()
    r = r.point(lambda v: min(255, int(v * WARMTH[0])))
    g = g.point(lambda v: min(255, int(v * WARMTH[1])))
    b = b.point(lambda v: min(255, int(v * WARMTH[2])))
    im = Image.merge("RGB", (r, g, b))
    return im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=52, threshold=3))


def main():
    cfg = json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8"))
    picks = cfg["picks"]
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    OUT.mkdir(parents=True, exist_ok=True)
    REAL.mkdir(parents=True, exist_ok=True)

    made, missing, real_count = 0, [], 0
    for slug, spec in picks.items():
        if only and slug not in only:
            continue
        src, is_real = load_source(slug, spec.get("pick", 0))
        if not src:
            missing.append(slug)
            continue
        real_count += is_real
        try:
            im = Image.open(src).convert("RGB")
        except Exception as e:
            print(f"  ! {slug}: {e}")
            missing.append(slug)
            continue
        targets = dict(SIZES)
        if slug in HERO_SLUGS:
            targets["@wide"] = WIDE
        for suffix, size in targets.items():
            out = OUT / f"{slug}{suffix}.webp"
            g = grade(crop(im, size, spec))
            q = {"": 76, "@sm": 70, "@wide": 52}[suffix]
            g.save(out, "WEBP", quality=q, method=6)
            made += 1
        flag = " (REAL PHOTO)" if is_real else ""
        print(f"  {slug}{flag}")

    print(f"\n{made} files written to {OUT}")
    print(f"{real_count} slugs using real photos, {len(picks) - real_count} still on stock")
    if missing:
        print(f"MISSING: {', '.join(missing)}")


if __name__ == "__main__":
    main()

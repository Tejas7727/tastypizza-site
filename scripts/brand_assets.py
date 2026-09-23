"""Generate the favicon, touch icon and social share card into assets/brand/.

Run after build_photos.py (the share card uses a graded food photo).

    python scripts/brand_assets.py
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "assets" / "brand"
IMG = ROOT / "docs" / "assets" / "img"
FONTS = ROOT / "assets" / "fonts"

RED = (183, 0, 23)
PAPER = (255, 247, 234)
INK = (25, 19, 16)

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#B70017"/>
  <path d="M32 11 54 51a2 2 0 0 1-1.8 3H11.8A2 2 0 0 1 10 51z" fill="#FFF7EA"/>
  <circle cx="32" cy="30" r="4.4" fill="#B70017"/>
  <circle cx="22" cy="43" r="4" fill="#B70017"/>
  <circle cx="42" cy="43" r="4" fill="#B70017"/>
</svg>
"""


def ttf(name, size):
    """Brand type for composed images. Archivo ships as a variable font, so the
    weight is dialled in rather than picked from a file."""
    if name.startswith("archivo"):
        p = FONTS / "archivo-var.ttf"
        if p.exists():
            try:
                f = ImageFont.truetype(str(p), size)
                f.set_variation_by_axes([100, int(name.split("-")[1])])
                return f
            except Exception:
                pass
    p = FONTS / f"{name}.ttf"
    if p.exists():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except Exception:
        return ImageFont.load_default()


def touch_icon():
    im = Image.new("RGB", (180, 180), RED)
    d = ImageDraw.Draw(im)
    d.polygon([(90, 30), (152, 143), (28, 143)], fill=PAPER)
    for cx, cy, r in ((90, 84, 12), (62, 121, 11), (118, 121, 11)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED)
    im.save(BRAND / "icon-180.png")
    return "icon-180.png"


def og_card():
    W, H = 1200, 630
    base = IMG / "donair@wide.webp"
    if base.exists():
        bg = Image.open(base).convert("RGB")
        r = max(W / bg.width, H / bg.height)
        bg = bg.resize((round(bg.width * r), round(bg.height * r)), Image.LANCZOS)
        left = (bg.width - W) // 2
        bg = bg.crop((left, 0, left + W, H))
    else:
        bg = Image.new("RGB", (W, H), INK)

    # scrim so type always reads, whatever the photo does
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    for x in range(W):
        a = int(238 - 208 * min(1.0, max(0.0, (x - 40) / (W * 0.78))))
        sd.line([(x, 0), (x, H)], fill=(14, 9, 7, max(28, a)))
    card = Image.alpha_composite(bg.convert("RGBA"), scrim)
    d = ImageDraw.Draw(card)

    logo_p = BRAND / "logo.webp"
    if logo_p.exists():
        lg = Image.open(logo_p).convert("RGBA")
        lw = 300
        lg = lg.resize((lw, round(lg.height * lw / lg.width)), Image.LANCZOS)
        card.alpha_composite(lg, (64, 54))

    big = ttf("alfaslabone-400", 66)
    mid = ttf("archivo-700", 30)
    small = ttf("archivo-500", 25)

    d.text((64, 236), "Donairs, pizza and", font=big, fill=(255, 255, 255))
    d.text((64, 310), "garlic fingers.", font=big, fill=(143, 207, 239))
    d.text((64, 404), "760 Main Street, Dartmouth  ·  902-435-5700", font=mid, fill=(255, 247, 234))
    d.text((64, 448), "Open 7 days  ·  Friday till 2am", font=small, fill=(215, 200, 185))

    d.rounded_rectangle([64, 508, 64 + 268, 508 + 62], 31, fill=RED)
    d.text((96, 524), "See the menu", font=mid, fill=(255, 255, 255))

    card.convert("RGB").save(BRAND / "og.jpg", quality=86, optimize=True)
    return "og.jpg"


def main():
    BRAND.mkdir(parents=True, exist_ok=True)
    (BRAND / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    made = ["favicon.svg", touch_icon(), og_card()]
    print("wrote " + ", ".join(made) + f" into {BRAND}")


if __name__ == "__main__":
    main()

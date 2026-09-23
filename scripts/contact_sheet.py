"""Tile photo candidates into one image so they can be judged side by side.

    python scripts/contact_sheet.py poutine fish-and-chips     # one sheet per slug
    python scripts/contact_sheet.py --all
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "research" / "photo-candidates"
CELL = (320, 240)
COLS = 6


def sheet(slugs, out):
    rows = []
    for slug in slugs:
        files = sorted((CAND / slug).glob("*.jpg"))
        if files:
            rows.append((slug, files))
    if not rows:
        print("nothing to tile")
        return
    w = CELL[0] * COLS
    h = sum(CELL[1] + 22 for _ in rows)
    sheet = Image.new("RGB", (w, h), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    y = 0
    for slug, files in rows:
        d.text((6, y + 5), f"{slug}   (0..{len(files)-1})", fill=(255, 210, 90))
        y += 22
        for i, f in enumerate(files[:COLS]):
            try:
                im = Image.open(f).convert("RGB")
            except Exception:
                continue
            im = crop_fill(im, CELL)
            sheet.paste(im, (i * CELL[0], y))
            d.rectangle([i * CELL[0], y, i * CELL[0] + 26, y + 18], fill=(0, 0, 0))
            d.text((i * CELL[0] + 7, y + 4), str(i), fill=(255, 255, 255))
        y += CELL[1]
    sheet.save(out, quality=88)
    print(f"wrote {out}  ({sheet.size[0]}x{sheet.size[1]})")


def crop_fill(im, size):
    tw, th = size
    r = max(tw / im.width, th / im.height)
    im = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)
    l = (im.width - tw) // 2
    t = (im.height - th) // 2
    return im.crop((l, t, l + tw, t + th))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--all" in sys.argv or not args:
        args = sorted(p.name for p in CAND.iterdir() if p.is_dir())
    for i in range(0, len(args), 6):
        chunk = args[i:i + 6]
        sheet(chunk, CAND / f"_sheet-{i//6:02d}.jpg")

"""Download the site's webfonts once into assets/fonts/ so the page self-hosts them.

Self-hosting means no third-party request on page load, no layout shift, and the
site keeps working if Google Fonts is blocked. Both families are SIL Open Font
License, which permits this.

    python scripts/fetch_fonts.py
"""
import re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "fonts"
# A modern desktop UA is required or the CSS endpoint serves legacy formats.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

WANT = [
    ("alfaslabone-400", "Alfa+Slab+One:wght@400"),
    ("archivo-400", "Archivo:wght@400"),
    ("archivo-500", "Archivo:wght@500"),
    ("archivo-700", "Archivo:wght@700"),
    ("archivo-800", "Archivo:wght@800"),
]


def get(url, ua=True):
    req = urllib.request.Request(url, headers={"User-Agent": UA} if ua else {})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def fetch_ttf(name, repo_path):
    """Pillow can't read woff2, and the share card needs brand type, so pull the
    TTF straight from the google/fonts repo. These stay out of docs/ - they are
    only used to compose images."""
    dest = OUT / f"{name}.ttf"
    if dest.exists():
        print(f"  {dest.name} already here")
        return
    url = "https://raw.githubusercontent.com/google/fonts/main/" + repo_path
    try:
        dest.write_bytes(get(url, ua=False))
        print(f"  {dest.name}  {dest.stat().st_size // 1024} KB (image composition only)")
    except Exception as err:
        print(f"  ! {name}: {err}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in WANT:
        dest = OUT / f"{name}.woff2"
        if dest.exists():
            print(f"  {dest.name} already here")
            continue
        css = get(f"https://fonts.googleapis.com/css2?family={spec}&display=swap").decode("utf-8")
        # prefer the latin subset block
        blocks = css.split("@font-face")
        urls = []
        for b in blocks:
            m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", b)
            if m:
                urls.append((("latin" in b and "latin-ext" not in b), m.group(1)))
        if not urls:
            print(f"  ! {name}: no woff2 found")
            continue
        urls.sort(key=lambda t: not t[0])
        data = get(urls[0][1])
        dest.write_bytes(data)
        print(f"  {dest.name}  {len(data) // 1024} KB")

    for name, repo_path in (
        ("alfaslabone-400", "ofl/alfaslabone/AlfaSlabOne-Regular.ttf"),
        ("archivo-var", "ofl/archivo/Archivo%5Bwdth,wght%5D.ttf"),
    ):
        fetch_ttf(name, repo_path)
    print(f"\nfonts in {OUT}")


if __name__ == "__main__":
    main()

"""Write CREDITS.md listing the licence and author of every stock photo in use.

Most are CC-BY or CC-BY-SA, which require attribution. Run this after changing
which candidate a slug uses.

    python scripts/credits.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "research" / "photo-candidates" / "candidates.json"
PICKS = ROOT / "data" / "photos.json"
REAL = ROOT / "assets" / "photos-in"
OUT = ROOT / "CREDITS.md"


def main():
    picks = json.loads(PICKS.read_text(encoding="utf-8"))["picks"]
    cand = json.loads(CAND.read_text(encoding="utf-8")) if CAND.exists() else {}

    rows, real = [], []
    for slug, spec in sorted(picks.items()):
        if any((REAL / f"{slug}{ext}").exists() for ext in (".jpg", ".jpeg", ".png", ".webp")):
            real.append(slug)
            continue
        meta = None
        for r in cand.get(slug, []):
            if r.get("file") == f"{spec.get('pick', 0):02d}.jpg":
                meta = r
                break
        if not meta:
            rows.append((slug, "—", "—", ""))
            continue
        rows.append((slug, (meta.get("creator") or "Unknown").strip(),
                     meta.get("license") or "—", meta.get("source") or ""))

    lines = [
        "# Photo credits",
        "",
        "The food photography on this site is **stock, used as a placeholder** until Tasty",
        "Pizza's own photos replace it. Every image below is freely licensed for commercial",
        "use. Where the licence requires attribution, the author is named.",
        "",
        "To replace one, drop a real photo named after the slug into `assets/photos-in/`",
        "and it is used instead — see the README.",
        "",
    ]
    if real:
        lines += [f"**{len(real)} slugs now use real Tasty Pizza photography:** "
                  + ", ".join(f"`{s}`" for s in real), ""]
    lines += ["| Used for | Author | Licence | Source |", "|---|---|---|---|"]
    for slug, who, lic, src in rows:
        link = f"[original]({src})" if src else "—"
        lines.append(f"| `{slug}` | {who} | {lic} | {link} |")
    lines += [
        "",
        "## Video",
        "",
        "| Used for | Author | Licence | Source |",
        "|---|---|---|---|",
        "| hero clip (`assets/video/hero.*`) | Ruth Hartnup | CC BY 2.0 | "
        "[Bubbling baking pizza](https://commons.wikimedia.org/wiki/File:Bubbling_baking_pizza.webm) |",
        "",
        "Map tiles on the contact card are © OpenStreetMap contributors (ODbL).",
        "Typefaces: Alfa Slab One and Archivo, both SIL Open Font License, self-hosted.",
        "",
        "The Tasty Pizza logo and chef mascot belong to Tasty Pizza and are used unchanged.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} — {len(rows)} stock photos, {len(real)} real")


if __name__ == "__main__":
    main()

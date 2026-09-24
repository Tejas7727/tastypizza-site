"""Render the drawn artwork in every palette, so it can be judged before it ships.

    python scripts/poster_study.py   ->  research/_poster-study.html
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import art  # noqa: E402

OUT = ROOT / "research" / "_poster-study.html"
PAL = json.loads((ROOT / "data" / "palettes.json").read_text(encoding="utf-8"))["palettes"]


def main():
    rows = []
    for pid, p in PAL.items():
        chips = "".join(
            f'<div class="chip"><span style="background:{p[k]}"></span>'
            f'<b>{k}</b><i>{p["pantone"][k]}</i><u>{p[k]}</u></div>'
            for k in ("paper", "ink", "accent", "pop"))
        art_cells = "".join(
            f'<div class="cell">{art.illo(name)}<span>{name}</span></div>'
            for name in ("pizza", "donair", "garlic-fingers"))
        rows.append(f"""
  <section class="pal" style="--paper:{p['paper']};--ink:{p['ink']};--accent:{p['accent']};--pop:{p['pop']}">
    <header><h2>{p['name']}</h2><p>{p['note']}</p><div class="chips">{chips}</div></header>
    <div class="grid">{art_cells}</div>
  </section>""")

    html = """<!doctype html><meta charset="utf-8"><title>poster study</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#101010;color:#eee;font:15px/1.5 system-ui,sans-serif}
h1{font:700 20px system-ui;padding:20px 24px 6px;margin:0}
.lead{padding:0 24px 18px;color:#999;max-width:70ch}
.pal{background:var(--paper);color:var(--ink);padding:26px 24px 30px;margin:0 0 3px}
.pal header{display:grid;gap:8px;margin-bottom:18px}
.pal h2{margin:0;font:800 26px system-ui;letter-spacing:-.01em}
.pal p{margin:0;opacity:.72;max-width:60ch}
.chips{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}
.chip{background:#fff;border:1px solid rgba(0,0,0,.12);width:116px;font-size:10px;line-height:1.35;
 color:#111;box-shadow:0 1px 2px rgba(0,0,0,.12)}
.chip span{display:block;height:56px}
.chip b,.chip i,.chip u{display:block;padding:0 6px;text-decoration:none;font-style:normal}
.chip b{font-size:9px;letter-spacing:.09em;text-transform:uppercase;padding-top:5px;opacity:.55}
.chip i{font-weight:700;font-size:11px}
.chip u{opacity:.5;padding-bottom:5px;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.cell{background:var(--paper);border:1px solid color-mix(in srgb,var(--ink) 18%,transparent);
 border-radius:4px;padding:8px;display:grid;justify-items:center}
.cell span{font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.5;margin-top:4px}
.illo{width:100%;height:auto;max-width:330px;display:block}
</style>
<h1>Poster artwork &mdash; drawn, in every palette</h1>
<p class="lead">Every fill is a CSS variable, so one drawing prints in all five palettes. Checking
that the food still reads as food in each, and that the cool ink stays the stage rather than the
subject.</p>
""" + "".join(rows)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

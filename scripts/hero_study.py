"""A working prototype of the poster hero: the press run, the ink rail, the mark.

This is the thing to look at before committing the whole site to the direction —
it proves the movement, not just the colour.

    python scripts/hero_study.py   ->  research/_hero-study.html
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import art, mark  # noqa: E402

OUT = ROOT / "research" / "_hero-study.html"
DATA = json.loads((ROOT / "data" / "palettes.json").read_text(encoding="utf-8"))
PAL = DATA["palettes"]


def chip(pal, key):
    return (f'<div class="chip" data-chip="{key}">'
            f'<span class="chip-ink" style="background:{pal[key]}"></span>'
            f'<span class="chip-lab"><b>PANTONE&reg;</b><i>{pal["pantone"][key]}</i></span></div>')


def rail(pal):
    return ('<aside class="rail" aria-hidden="true">'
            + "".join(chip(pal, k) for k in ("ink", "accent", "pop"))
            + '</aside>')


def scene(pid, kicker, head, sub, illo_name):
    p = PAL[pid]
    return f"""
<section class="scene" data-palette="{pid}"
  style="--paper:{p['paper']};--ink:{p['ink']};--accent:{p['accent']};--pop:{p['pop']}">
  <div class="scene-in">
    <div class="copy">
      <p class="kicker">{kicker}</p>
      <h2 class="display">{head}</h2>
      <p class="sub">{sub}</p>
      <p class="swatchline"><b>{p['name']}</b> &mdash; {p['note']}</p>
    </div>
    <figure class="press">{art.illo(illo_name)}</figure>
  </div>
  {rail(p)}
</section>"""


def main():
    house = PAL["house"]
    css = (ROOT / "src" / "poster.css").read_text(encoding="utf-8")
    css = css.replace("url('fonts/", "url('../assets/fonts/")
    js = (ROOT / "src" / "poster.js").read_text(encoding="utf-8")

    scenes = (
        scene("house", "Halifax&rsquo;s official food", "Printed<br>fresh<br><em>daily.</em>",
              "Every section of this site is a three-ink screen print. Scroll and the plates "
              "come into register.", "pizza")
        + scene("donair", "The one we&rsquo;re known for", "Off the<br><em>spit.</em>",
                "Aubergine ground, terracotta meat. The cool ink is the stage; the food always "
                "wears the warm ones.", "donair")
        + scene("garden", "Never served without the sauce", "Garlic<br><em>fingers.</em>",
                "Same drawing, different palette. Nothing was redrawn &mdash; every fill is a "
                "CSS variable.", "garlic-fingers")
    )

    html = f"""<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Poster direction — hero study</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<style>{css}</style>
</head>
<body class="study"
  style="--paper:{house['paper']};--ink:{house['ink']};--accent:{house['accent']};--pop:{house['pop']}">

<header class="mast">
  <a class="brand" href="#">{mark.lockup(40)}</a>
  <nav><a href="#">Menu</a><a href="#">Deals</a><a href="#">Find us</a></nav>
  <a class="btn" href="#">902-435-5700</a>
</header>

<section class="hero" data-palette="house">
  <div class="hero-in">
    <div class="copy">
      <p class="kicker">Main Street, Dartmouth &middot; since 2005</p>
      <h1 class="display">Donairs,<br>pizza and<br><em>garlic fingers.</em></h1>
      <p class="sub">Dough and sauce made fresh every day. Kitchen&rsquo;s on till 2am Friday.</p>
      <div class="acts"><a class="btn btn-solid" href="#">See the menu</a>
        <a class="btn" href="#">902-435-5700</a></div>
    </div>
    <figure class="press press-hero">{art.illo('pizza')}</figure>
  </div>
  {rail(house)}
  <span class="runline">4 colour &middot; 1 pass &middot; Tasty Pizza press</span>
</section>

{scenes}

<section class="marks">
  <h2>The mark</h2>
  <div class="mark-grid">
    <div class="mark-cell"><div class="big">{mark.emblem(150)}</div><span>emblem</span></div>
    <div class="mark-cell"><div class="big">{mark.emblem(150, pulled=False)}</div><span>whole pie, no pull</span></div>
    <div class="mark-cell"><div class="big">{mark.wordmark()}</div><span>wordmark, out of register</span></div>
    <div class="mark-cell"><div class="big">{mark.lockup(56)}</div><span>lockup</span></div>
    <div class="mark-cell"><div class="big">{mark.emblem(150, one_ink=True)}</div><span>one ink &mdash; vinyl, stamp, embroidery</span></div>
    <div class="mark-cell tiny"><div class="big">{mark.emblem(30)}{mark.emblem(22)}{mark.emblem(16)}</div><span>28 / 20 / 16px</span></div>
  </div>
</section>

<script>{js}</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

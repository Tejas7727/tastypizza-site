"""Direction 2 — white ground, real photography, pizza first.

    python scripts/brand_study.py   ->  research/_brand-study.html
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "research" / "_brand-study.html"
MENU = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
SITE = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
PHOTOS = json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8"))["picks"]

IMG = "../assets/img/"

TICKER = ["Dough made fresh every morning", "Open till 2am Friday", "760 Main St, Dartmouth",
          "Halifax's official food, done properly", "Free parking out front",
          "Debit at your door"]


def find(name):
    for c in MENU["categories"]:
        for g in c["groups"]:
            for it in g["items"]:
                if it["name"] == name:
                    ps = it.get("prices") or ([it["price"]] if "price" in it else [])
                    if not ps and it.get("tier"):
                        ps = g["tiers"][str(it["tier"])]
                    lo = min([p for p in ps if p is not None], default=None)
                    return it, lo, len([p for p in ps if p is not None]) > 1
    return None, None, False


def hit(name, no, tag=""):
    it, price, many = find(name)
    if not it:
        return ""
    slug = it.get("photo") or "cheese-pizza"
    alt = PHOTOS.get(slug, {}).get("alt", it["name"])
    tags = "".join(f'<span class="tag tag-{t}">{lbl}</span>'
                   for t, lbl in ([("veg", "Vegetarian")] if "veg" in it.get("tags", []) else [])
                   + ([("hot", "Most ordered")] if "popular" in it.get("tags", []) else []))
    return f"""
      <article class="hit">
        <div class="hit-media"><span class="hit-no">{no:02d}</span>
          <img src="{IMG}{slug}.webp" srcset="{IMG}{slug}@sm.webp 400w, {IMG}{slug}.webp 800w"
               sizes="(max-width:920px) 46vw, 300px" width="800" height="600" loading="lazy"
               alt="{alt}"></div>
        <div class="hit-body">
          <h3>{it['name']}</h3>
          <p>{it.get('desc','')}</p>
          <div class="hit-foot">
            <span class="price"><small>{'from' if many else ''}</small>${price:.2f}</span>
            <button class="add" type="button">Add</button>
          </div>
          <div style="display:flex;gap:.35rem;flex-wrap:wrap">{tags}</div>
        </div>
      </article>"""


def main():
    css = (ROOT / "src" / "brand.css").read_text(encoding="utf-8")
    js = (ROOT / "src" / "brand.js").read_text(encoding="utf-8")
    ticker = "".join(f"<span>{t}</span>" for t in TICKER)

    hits = "".join(hit(n, i + 1) for i, n in enumerate(
        ["All Dressed", "Meat Lovers", "Garlic Fingers", "Donair Pizza",
         "Vegetarian", "Classic Poutine"]))

    html = f"""<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tasty Pizza — brand direction</title>
<link rel="stylesheet" href="https://unpkg.com/lenis@1.3.26/dist/lenis.css">
<style>{css}</style>
</head>
<body>

<header class="mast">
  <a class="brand" href="#"><img src="../assets/img/logo-clean.webp"
     srcset="../assets/img/logo-clean.webp 414w, ../assets/img/logo-clean@2x.webp 828w"
     width="414" height="172" alt="Tasty Pizza"></a>
  <nav><a href="#menu">Menu</a><a href="#">Deals</a><a href="#">Find us</a></nav>
  <span class="openpill">Open till 11pm</span>
  <a class="btn btn-red" href="tel:+19024355700">902-435-5700</a>
</header>

<section class="hero">
  <div class="wrap hero-in">
    <div>
      <p class="eyebrow" data-anim>760 Main Street &middot; Twenty years</p>
      <h1 class="display" data-anim>Dartmouth&rsquo;s<br><em>pizza.</em></h1>
      <p class="lede" data-anim>Dough and sauce made fresh every morning, hand-stretched, out of
        a deck oven on Main Street. The donairs are famous. The pizza is the reason.</p>
      <div class="acts" data-anim>
        <a class="btn btn-red" href="#menu">See the menu</a>
        <a class="btn btn-line" href="tel:+19024355700">Call to order</a>
      </div>
    </div>

    <figure class="turntable" data-anim="grow">
      <span class="badge"><span><b>2am</b>Friday</span></span>
      <div class="disc disc-spin">
        <img src="{IMG}meat-lovers-pizza.webp" width="800" height="600"
             alt="A pepperoni pizza straight out of the oven" fetchpriority="high">
      </div>
      <svg class="orbit" viewBox="0 0 100 100" aria-hidden="true">
        <defs><path id="ring" d="M50,50 m-48.4,0 a48.4,48.4 0 1,1 96.8,0 a48.4,48.4 0 1,1 -96.8,0"/></defs>
        <text><textPath href="#ring" startOffset="0">
          Fresh dough daily &middot; Hand stretched &middot; Deck oven &middot; 760 Main St &middot;
        </textPath></text>
      </svg>
    </figure>
  </div>
</section>

<div class="ticker" aria-hidden="true"><div class="ticker-row">{ticker}{ticker}</div></div>

<section class="band" id="menu">
  <div class="wrap">
    <header class="sec-head" data-anim>
      <div><p class="num">01 &mdash; The menu</p>
        <h2>What people<br>actually order</h2></div>
      <a class="btn btn-line" href="#">All 152 items</a>
    </header>
    <div class="hits" data-stagger>{hits}</div>
  </div>
</section>

<section class="band band-paper">
  <div class="wrap feature">
    <figure class="feature-media" data-anim="mask">
      <img src="{IMG}garlic-fingers.webp" width="800" height="600" loading="lazy"
           alt="Garlic fingers with a pot of donair dipping sauce">
    </figure>
    <div>
      <p class="num" data-anim>02 &mdash; The house</p>
      <h2 class="display" data-anim style="font-size:clamp(2.2rem,4.6vw,3.6rem)">Garlic fingers,<br>donair sauce.</h2>
      <p class="lede" data-anim>The pan comes out scored into fingers, mozzarella still moving.
        The sauce is not optional and we will not pretend otherwise.</p>
      <div class="rule-list" data-anim>
        <div><span>9&Prime; small</span><b>$10.25</b></div>
        <div><span>12&Prime; medium</span><b>$13.95</b></div>
        <div><span>16&Prime; large</span><b>$17.95</b></div>
        <div><span>18&Prime; extra large</span><b>$22.45</b></div>
      </div>
    </div>
  </div>
</section>

<section class="band">
  <div class="wrap feature">
    <div>
      <p class="num" data-anim>03 &mdash; Also famous</p>
      <h2 class="display" data-anim style="font-size:clamp(2.2rem,4.6vw,3.6rem)">The donair,<br>done right.</h2>
      <p class="lede" data-anim>Halifax made it the official food of the city. We have been making
        it on Main Street for twenty years &mdash; on the pita, on a pizza, in an egg roll, or on
        a stick if you are feeling brave.</p>
      <div class="acts" data-anim><a class="btn btn-line" href="#">See the donair menu</a></div>
    </div>
    <figure class="feature-media" data-anim="mask">
      <img src="{IMG}donair.webp" width="800" height="600" loading="lazy"
           alt="A donair in pita bread with tomato, onion and donair sauce">
    </figure>
  </div>
</section>

<script src="https://unpkg.com/lenis@1.3.26/dist/lenis.min.js"></script>
<script>{js}</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

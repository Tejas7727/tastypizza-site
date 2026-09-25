#!/usr/bin/env python3
"""Build the Tasty Pizza site from data/*.json into docs/.

    python build.py

Standard library only - nothing to install. Everything the site says comes from the
JSON files in data/. Change those, run this, and the site updates. The GitHub Action
does exactly that on every push, so editing a price on github.com is enough.
"""
import json, shutil, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from kit import (  # noqa: E402
    DATA, OUT, SRC, add_button, e, fmt_hour, from_price, icon, item_prices,
    load, money, page, photo_tag, slugify, visible,
)


# ---------------------------------------------------------------- home page

def collect_hits(site, menu):
    """The six home-page cards, named in site.json so the owner picks them."""
    index = {}
    for cat in visible(menu["categories"]):
        for g in cat["groups"]:
            for it in visible(g["items"]):
                index.setdefault(it["name"], (cat, g, it))
    out = []
    for name in site.get("hits", []):
        if name in index:
            out.append(index[name])
        else:
            print(f"  ! site.json hits: no menu item called '{name}'")
    return out


def hero(site):
    """Full viewport, and the food is moving — a pizza bubbling in the oven,
    with heat rising off it. The poster carries the frame until the video is
    decoded, and is all anyone sees under prefers-reduced-motion."""
    return f"""
<section class="hero">
  <div class="hero-media">
    <video data-hero-video poster="assets/video/hero-poster.webp" autoplay muted loop playsinline
           preload="auto" aria-label="A pizza bubbling in the oven" width="1440" height="810">
      <source src="assets/video/hero.mp4" type="video/mp4">
      <img src="assets/video/hero-poster.webp" width="1440" height="810"
           alt="A pizza bubbling in the oven">
    </video>
    <div class="hero-scrim"></div>
  </div>
  <div class="steam" aria-hidden="true">
    <i style="--x:38%;--w:170px;--d:12s;--delay:0s"></i>
    <i style="--x:54%;--w:130px;--d:9.5s;--delay:2.4s"></i>
    <i style="--x:68%;--w:190px;--d:14s;--delay:5.1s"></i>
  </div>
  <div class="hero-in">
    <p class="kicker">{e(site['claim'])}</p>
    <h1>Donairs, pizza and<br>garlic fingers on<br><em>Main Street.</em></h1>
    <p class="lede">{e(site['tagline'])}. Dough and sauce made fresh every day.</p>
    <div class="hero-act">
      <a class="btn btn-red big" href="menu.html">{icon('bag')}<span>See the menu</span></a>
      <a class="btn btn-bone big" href="tel:{site['phoneLink']}">{icon('phone')}<span>{site['phone']}</span></a>
    </div>
    <p class="hero-open"><span class="openpill big" data-clock hidden></span></p>
  </div>
  <span class="scrollcue" aria-hidden="true">Scroll</span>
</section>"""


def hits_section(site, menu):
    cards = []
    for cat, g, it in collect_hits(site, menu):
        p = from_price(it, g)
        many = len([x for x in item_prices(it, g) if x is not None]) > 1
        cards.append(f"""
      <article class="hit">
        <a class="hit-media" href="menu.html#{cat['id']}" tabindex="-1" aria-hidden="true">{photo_tag(it['photo'], it.get('desc') or it['name'], sizes='(max-width:700px) 46vw, 300px')}</a>
        <div class="hit-body">
          <h3><a href="menu.html#{cat['id']}">{e(it['name'])}</a></h3>
          <p>{e(it.get('desc', ''))}</p>
          <div class="hit-foot">
            <span class="price">{('from ' if many else '') + money(p)}</span>
            {add_button(it['name'], p)}
          </div>
        </div>
      </article>""")
    return f"""
<section class="band band-bone" id="hits">
  <div class="wrap">
    <header class="sec-head">
      <h2>What people actually order</h2>
      <a class="ul" href="menu.html">See the whole menu <span aria-hidden="true">&rarr;</span></a>
    </header>
    <div class="hits">{''.join(cards)}</div>
  </div>
</section>"""


def builder_section(menu):
    b = menu["builder"]
    sizes = "".join(
        f'<button class="chip" type="button" data-size="{i}" role="radio" '
        f'aria-checked="{"true" if i == 1 else "false"}"{" data-on" if i == 1 else ""}>{e(s)}</button>'
        for i, s in enumerate(b["sizes"]))
    crusts = "".join(
        f'<button class="chip" type="button" data-crust="{e(c["name"])}" data-sur="{c["surcharge"]}" '
        f'role="radio" aria-checked="{"true" if i == 0 else "false"}"{" data-on" if i == 0 else ""}>'
        f'{e(c["name"])}' + (f'<em>+{money(c["surcharge"])}</em>' if c["surcharge"] else "") + "</button>"
        for i, c in enumerate(menu["crusts"]))
    tops = "".join(
        f'<button class="topbtn" type="button" data-top="{e(t)}" aria-pressed="false">'
        f'<i class="tdot t-{slugify(t)}" aria-hidden="true"></i>{e(t)}</button>'
        for t in menu["toppings"])
    return f"""
<section class="band band-ink" id="build">
  <div class="wrap build">
    <div class="build-copy">
      <p class="kicker">The fun part</p>
      <h2>Build it on the peel</h2>
      <p class="lede">Pick a size, start tapping. The price moves as you go, so there are no
        surprises when you get to the counter.</p>
      <div class="build-price">
        <span class="bp-label">Your pizza</span>
        <strong class="till" data-build-price>$12.90</strong>
        <span class="bp-note" data-build-note>12&quot; Medium &middot; just cheese</span>
      </div>
      <div class="build-act">
        {add_button('Custom pizza', None, 'Add to my order')}
        <button class="linkbtn" type="button" data-build-reset>Start over</button>
      </div>
    </div>

    <div class="build-stage">
      <div class="peel" data-peel>
        <span class="peel-handle" aria-hidden="true"></span>
        <span class="peel-board" aria-hidden="true"></span>
        <div class="dough" data-dough>
          <span class="crustring" aria-hidden="true"></span>
          <span class="sauce" aria-hidden="true"></span>
          <span class="cheese" aria-hidden="true"></span>
          <div class="tops" data-tops></div>
        </div>
      </div>
      <img class="chef chef-build" src="assets/img/chef.png" width="231" height="100" alt="" data-chef aria-hidden="true">
    </div>

    <div class="build-ctrl">
      <div class="ctrl">
        <h3>Size</h3>
        <div class="chips" role="radiogroup" aria-label="Pizza size" data-sizes>{sizes}</div>
      </div>
      <div class="ctrl">
        <h3>Crust</h3>
        <div class="chips" role="radiogroup" aria-label="Crust" data-crusts>{crusts}</div>
      </div>
      <div class="ctrl ctrl-wide">
        <h3>Toppings <span class="ctrl-note" data-top-count>0 of {b['maxToppings']}</span></h3>
        <div class="tops-grid" data-topgrid>{tops}</div>
        <p class="ctrl-hint">Five toppings makes it a {e(b['specialName'])} &mdash; we price it that way
          automatically.</p>
      </div>
    </div>
  </div>
</section>"""


def deals_section(deals):
    today = date.today().isoformat()
    live = [d for d in deals["deals"]
            if d.get("active") and (not d.get("until") or d["until"] >= today)]
    cards = []
    for d in live:
        save = ""
        if d.get("compareAt") and d["compareAt"] > d["price"]:
            save = f'<span class="save">Save {money(d["compareAt"] - d["price"])}</span>'
        badge = f'<span class="badge">{e(d["badge"])}</span>' if d.get("badge") else ""
        addon = ""
        if d.get("addOn"):
            addon = (f'<label class="addon"><input type="checkbox" data-addon="{d["addOn"]["price"]}">'
                     f'<span>{e(d["addOn"]["name"])} <b>+{money(d["addOn"]["price"])}</b></span></label>')
        cards.append(f"""
      <article class="deal">
        {badge}
        <div class="deal-media">{photo_tag(d.get('photo'), d['name'], sizes='(max-width:700px) 92vw, 300px')}</div>
        <div class="deal-body">
          <h3>{e(d['name'])}</h3>
          <p>{e(d.get('desc', ''))}</p>
          {addon}
          <div class="deal-foot">
            <span class="price big" data-deal-price="{d['price']}">{money(d['price'])}</span>{save}
            {add_button(d['name'], d['price'], 'Add')}
          </div>
        </div>
      </article>""")
    return f"""
<section class="band band-checker" id="deals">
  <div class="wrap">
    <header class="sec-head">
      <h2>Deals on right now</h2>
      <p class="sec-sub">{len(live)} running. All prices before tax.</p>
    </header>
    <div class="deals">{''.join(cards)}</div>
  </div>
</section>"""


def order_section(site):
    d, o = site["delivery"], site["ordering"]
    plat = []
    for key, name, sub in (("doordash", "DoorDash", "Delivery &amp; pickup, tracked"),
                           ("ubereats", "Uber Eats", "Delivery &amp; pickup, tracked"),
                           ("skipthedishes", "SkipTheDishes", "Delivery")):
        if o.get(key):
            plat.append(f'<a class="plat" href="{o[key]}" target="_blank" rel="noopener">'
                        f'<span class="plat-n">{name}</span><span class="plat-s">{sub}</span>'
                        f'<span class="plat-go" aria-hidden="true">{icon("chev")}</span></a>')
    return f"""
<section class="band band-bone" id="order">
  <div class="wrap">
    <header class="sec-head"><h2>Three ways to get it</h2></header>
    <div class="order-grid">
      <div class="ord ord-main">
        <h3>Call us &mdash; it's the fastest</h3>
        <p>Straight through to the kitchen. Tell us what you want and we'll tell you when it's ready.</p>
        <a class="btn btn-red big" href="tel:{site['phoneLink']}">{icon('phone')}<span>{site['phone']}</span></a>
        <p class="ord-note">Eat in, pick up or delivery. Debit at your door on request.</p>
      </div>
      <div class="ord">
        <h3>Order online</h3>
        <p>Through our delivery partners.</p>
        <div class="plats">{''.join(plat)}</div>
      </div>
      <div class="ord">
        <h3>Delivery</h3>
        <p class="big-fact">{money(d['minimum'])}<span>minimum order</span></p>
        <p class="big-fact">{money(d['fee'])}<span>delivery charge</span></p>
        <p class="ord-note">{e(d['note'])}</p>
        <p class="muted">{e(', '.join(d['areas']))}</p>
      </div>
    </div>
  </div>
</section>"""


def find_section(site):
    facts = "".join(f'<li>{icon(f["icon"])}<span>{e(f["label"])}</span></li>' for f in site["facts"])
    hrs = "".join(
        f'<div class="hrow" data-day="{h["day"]}"><dt>{h["day"]}</dt><dd>'
        + ("Closed" if h.get("closed") else f'{fmt_hour(h["open"])} &ndash; {fmt_hour(h["close"])}')
        + "</dd></div>" for h in site["hours"])
    lat, lng = site["geo"]["lat"], site["geo"]["lng"]
    bbox = f"{lng - 0.010},{lat - 0.005},{lng + 0.010},{lat + 0.005}"
    return f"""
<section class="band band-cream" id="find">
  <div class="wrap find">
    <div class="find-copy">
      <p class="kicker">Come and get it</p>
      <h2>760 Main Street</h2>
      <p class="lede">Just off the #7, free parking out front.</p>
      <a class="btn btn-red" href="{site['mapsDirectionsUrl']}" target="_blank" rel="noopener">{icon('pin')}<span>Get directions</span></a>
      <ul class="facts">{facts}</ul>
      <h3 class="find-h3">Open 7 days</h3>
      <dl class="hours big">{hrs}</dl>
      <p class="find-late">Kitchen's on until <strong>2am Friday</strong> and <strong>1am Saturday</strong>.</p>
    </div>
    <a class="mapcard" href="{site['mapsUrl']}" target="_blank" rel="noopener"
       aria-label="Open Tasty Pizza, 760 Main Street, in Google Maps">
      <iframe src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&amp;layer=mapnik&amp;marker={lat},{lng}"
              title="Map showing 760 Main Street, Dartmouth" loading="lazy" tabindex="-1" aria-hidden="true"></iframe>
      <span class="mapcard-cta">{icon('pin')}<span>Open in Google Maps</span></span>
      <span class="mapcard-attr">&copy; OpenStreetMap contributors</span>
    </a>
  </div>
</section>"""


def build_home(site, menu, deals):
    body = (hero(site) + hits_section(site, menu) + builder_section(menu)
            + deals_section(deals) + order_section(site) + find_section(site))
    # The builder's price maths comes straight from data/menu.json, so repricing
    # a pizza never means touching JavaScript.
    build_js = ("<script>window.BUILD=" + json.dumps({
        "sizes": menu["builder"]["sizes"],
        "priceByToppingCount": menu["builder"]["priceByToppingCount"],
        "maxToppings": menu["builder"]["maxToppings"],
        "specialName": menu["builder"]["specialName"],
    }, separators=(",", ":")) + ";</script>")
    return page(site["seo"]["title"], site["seo"]["description"], body, site, "home",
                extra_js=build_js)


# ---------------------------------------------------------------- menu page

TAG_LABELS = {"veg": "Vegetarian", "spicy": "Spicy", "seafood": "Seafood",
              "chicken": "Chicken", "donair": "Donair", "popular": "Popular",
              "glutenfree": "Gluten free", "new": "New"}


def render_group(g):
    sizes = g.get("sizes")
    items = visible(g["items"])
    rows = []
    for it in items:
        prices = item_prices(it, g)
        tags = it.get("tags", [])
        taghtml = "".join(f'<span class="tag t-{t}">{TAG_LABELS.get(t, t)}</span>' for t in tags)
        desc = f'<p class="row-desc">{e(it["desc"])}</p>' if it.get("desc") else ""
        media = ""
        if it.get("photo"):
            media = f'<div class="row-media">{photo_tag(it["photo"], it.get("desc") or it["name"], sizes="(max-width:700px) 30vw, 150px")}</div>'

        if it.get("builder"):
            # not a priced dish: the row that sends you to the pizza builder.
            # Without this it would render as "Call for price".
            frm = min(p for p in load("menu")["builder"]["priceByToppingCount"][0] if p is not None)
            price_block = (f'<div class="row-one">'
                           f'<span class="price"><small>from</small> {money(frm)}</span>'
                           f'<a class="add" href="index.html#build">Build it</a></div>')
        elif sizes and len(prices) > 1:
            cells = "".join(
                (f'<button class="pcell" type="button" data-add="{e(it["name"])} ({e(sz)})" data-price="{p}">'
                 f'<span class="pcell-sz">{e(sz)}</span><span class="pcell-p">{money(p)}</span></button>')
                if p is not None else
                f'<span class="pcell pcell-off"><span class="pcell-sz">{e(sz)}</span><span class="pcell-p">&ndash;</span></span>'
                for sz, p in zip(sizes, prices))
            price_block = f'<div class="sizecols">{cells}</div>'
        else:
            p = prices[0]
            price_block = (f'<div class="row-one">'
                           f'<span class="price">{money(p)}</span>{add_button(it["name"], p)}</div>')

        rows.append(f"""
        <li class="row" data-item data-name="{e(it['name'].lower())}" data-tags="{e(' '.join(tags))}">
          {media}
          <div class="row-body">
            <h4>{e(it['name'])} {taghtml}</h4>
            {desc}
          </div>
          {price_block}
        </li>""")

    note = f'<p class="grp-note">{e(g["note"])}</p>' if g.get("note") else ""
    return f"""
      <section class="grp" id="{e(g['id'])}">
        <header class="grp-head">
          <h3>{e(g['name'])}</h3>
          {note}
        </header>
        <ul class="rows">{''.join(rows)}</ul>
      </section>"""


def build_menu(site, menu, deals):
    rail = "".join(
        f'<a class="railitem" href="#{e(c["id"])}">{e(c["name"])}</a>' for c in visible(menu["categories"]))
    tags = "".join(
        f'<button class="filter" type="button" data-filter="{t}">{lbl}</button>'
        for t, lbl in (("popular", "Popular"), ("donair", "Donair"), ("veg", "Vegetarian"),
                       ("chicken", "Chicken"), ("seafood", "Seafood"), ("spicy", "Spicy"),
                       ("glutenfree", "Gluten free")))

    cats = []
    for c in visible(menu["categories"]):
        groups = "".join(render_group(g) for g in c["groups"])
        cats.append(f"""
    <section class="cat" id="{e(c['id'])}">
      <header class="cat-head">
        <h2>{e(c['name'])}</h2>
        <p>{e(c.get('blurb', ''))}</p>
      </header>
      {groups}
    </section>""")

    tops = ", ".join(menu["toppings"])
    sp = menu["specialToppings"]
    body = f"""
<section class="menu-top">
  <div class="wrap">
    <p class="kicker">Everything we make</p>
    <h1>The menu</h1>
    <p class="lede">Tap a price to add it to your order. Prices are before tax.</p>
  </div>
</section>

<div class="toolbar" data-toolbar>
  <div class="wrap toolbar-in">
    <label class="search">
      {icon('search')}
      <input type="search" placeholder="Search the menu&hellip;" data-search aria-label="Search the menu">
      <button class="search-x" type="button" data-search-clear hidden aria-label="Clear search">{icon('x')}</button>
    </label>
    <div class="filters" data-filters>{tags}</div>
  </div>
  <nav class="rail" aria-label="Menu sections"><div class="wrap rail-in">{rail}</div></nav>
</div>

<p class="noresult" data-noresult hidden>Nothing matches that. <button class="linkbtn" type="button" data-search-clear>Show everything</button></p>

<div class="wrap menu-body">
  {''.join(cats)}

  <section class="cat" id="toppings">
    <header class="cat-head"><h2>Toppings</h2><p>On any pizza, any size.</p></header>
    <div class="grp">
      <p class="toplist">{e(tops)}</p>
      <h3 class="grp-h">Special toppings</h3>
      <p class="grp-note">{e(', '.join(sp['names']))}</p>
      <div class="sizecols sizecols-bare">
        {''.join(f'<span class="pcell pcell-off"><span class="pcell-sz">{e(s)}</span><span class="pcell-p">{money(p)}</span></span>' for s, p in zip(['9" S', '12" M', '16" L', '18" XL'], sp['prices']))}
      </div>
    </div>
  </section>
</div>"""
    return page("Menu — Tasty Pizza, Dartmouth NS",
                "The full Tasty Pizza menu: donairs, pizza, garlic fingers, poutine, subs, "
                "seafood, burritos and wings. Prices for every size.",
                body, site, "menu")


# ---------------------------------------------------------------- assets + main

def copy_assets():
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "app.js"):
        src = SRC / name
        if src.exists():
            shutil.copy2(src, OUT / "assets" / name)
    fonts = ROOT / "assets" / "fonts"
    if fonts.exists():
        dst = OUT / "assets" / "fonts"
        dst.mkdir(parents=True, exist_ok=True)
        for f in fonts.glob("*.woff2"):
            shutil.copy2(f, dst / f.name)
    video = ROOT / "assets" / "video"
    if video.exists():
        dst = OUT / "assets" / "video"
        dst.mkdir(parents=True, exist_ok=True)
        for f in video.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)
    brand = ROOT / "assets" / "brand"
    if brand.exists():
        for f in brand.iterdir():
            if f.is_file():
                shutil.copy2(f, OUT / "assets" / "img" / f.name)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    # While "live" is false this is a preview build, and a preview that Google indexes
    # would compete with the real tastypizza.ca in search.
    if load("site").get("live"):
        robots = "User-agent: *\nAllow: /\nSitemap: https://tastypizza.ca/sitemap.xml\n"
    else:
        robots = ('# Preview build. Set "live": true in data/site.json when this goes to\n'
                  "# tastypizza.ca, and search engines will be allowed in.\n"
                  "User-agent: *\nDisallow: /\n")
    (OUT / "robots.txt").write_text(robots, encoding="utf-8")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'<url><loc>https://tastypizza.ca/</loc><lastmod>{date.today()}</lastmod><priority>1.0</priority></url>\n'
        f'<url><loc>https://tastypizza.ca/menu.html</loc><lastmod>{date.today()}</lastmod><priority>0.9</priority></url>\n'
        '</urlset>\n', encoding="utf-8")


def main():
    site, menu, deals = load("site"), load("menu"), load("deals")
    OUT.mkdir(parents=True, exist_ok=True)
    copy_assets()
    (OUT / "index.html").write_text(build_home(site, menu, deals), encoding="utf-8")
    (OUT / "menu.html").write_text(build_menu(site, menu, deals), encoding="utf-8")

    n_items = sum(len(visible(g["items"]))
                  for c in visible(menu["categories"]) for g in c["groups"])
    n_deals = len([d for d in deals["deals"] if d.get("active")])
    print(f"built docs/index.html and docs/menu.html")
    print(f"  {n_items} menu items across {len(visible(menu['categories']))} categories, {n_deals} live deals")


if __name__ == "__main__":
    main()

"""Direction 2, rebuilt around the order path.

Structure follows the research, not taste:
  hero + quick-pick   the four doors into the menu, in the gaze path
  deals               offers come before browsing, because offers start orders
  popular             six items, ONE flagged
  build your own      the toy, with the pizza pinned on small screens
  how to order        three steps, for people who do not shop online much
  find us             hours, areas served, map

    python scripts/brand_study.py   ->  research/_brand-study.html
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "research" / "_brand-study.html"
MENU = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
SITE = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
DEALS = json.loads((ROOT / "data" / "deals.json").read_text(encoding="utf-8"))
PHOTOS = json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8"))["picks"]

IMG = "../assets/img/"
TICKER = ["Dough made fresh every morning", "Open till 2am Friday", "760 Main St, Dartmouth",
          "Free parking out front", "Delivery across Cole Harbour & Westphal",
          "Debit at your door"]


def money(v):
    return f"${v:,.2f}"


def find(name):
    for c in MENU["categories"]:
        for g in c["groups"]:
            for it in g["items"]:
                if it["name"] == name:
                    ps = it.get("prices") or ([it["price"]] if "price" in it else [])
                    if not ps and it.get("tier"):
                        ps = g["tiers"][str(it["tier"])]
                    vals = [p for p in ps if p is not None]
                    return it, (min(vals) if vals else None), len(vals) > 1
    return None, None, False


def card(name, flag=None):
    """A food card. `flag` is the single highlight a group is allowed."""
    it, price, many = find(name)
    if not it:
        return ""
    slug = it.get("photo") or "cheese-pizza"
    alt = PHOTOS.get(slug, {}).get("alt", it["name"])
    veg = '<span class="tag tag-veg">Vegetarian</span>' if "veg" in it.get("tags", []) else ""
    flag_html = f'<span class="card-flag">{flag}</span>' if flag else ""
    return f"""
        <article class="card">{flag_html}
          <div class="card-media">
            <img src="{IMG}{slug}.webp" srcset="{IMG}{slug}@sm.webp 400w, {IMG}{slug}.webp 800w"
                 sizes="(max-width:620px) 46vw, 280px" width="800" height="600" loading="lazy"
                 alt="{alt}"></div>
          <div class="card-body">
            <h3>{it['name']}</h3>
            <p>{it.get('desc','')}</p>
            {veg}
            <div class="card-foot">
              <span class="price"><small>{'from' if many else ''}</small>{money(price)}</span>
              <button class="add" type="button" data-add="{it['name']}">Add</button>
            </div>
          </div>
        </article>"""


def deal_card(d, flag=None):
    slug = d.get("photo", "cheese-pizza")
    save = ""
    if d.get("compareAt") and d["compareAt"] > d["price"]:
        save = f'<span class="save">Save {money(d["compareAt"] - d["price"])}</span>'
    flag_html = f'<span class="card-flag">{flag}</span>' if flag else ""
    return f"""
        <article class="deal">{flag_html}
          <img src="{IMG}{slug}.webp" width="800" height="600" loading="lazy" alt="">
          <div class="deal-in">
            <h3>{d['name']}</h3>
            <p>{d.get('desc','')}</p>
            <div class="deal-foot">
              <span class="price">{money(d['price'])}</span>{save}
              <button class="add" type="button" data-add="{d['name']}">Add</button>
            </div>
          </div>
        </article>"""


def menu_schema():
    """Full Menu schema. Restaurants with it get roughly 25% more clicks from
    search than those without, and it is what AI answers and voice assistants
    read. This is the single cheapest SEO win available to the site."""
    sections = []
    for c in MENU["categories"]:
        items = []
        for g in c["groups"]:
            for it in g["items"]:
                if it.get("hidden"):
                    continue
                ps = it.get("prices") or ([it["price"]] if "price" in it else [])
                if not ps and it.get("tier"):
                    ps = g["tiers"][str(it["tier"])]
                vals = [p for p in ps if p is not None]
                if not vals:
                    continue
                entry = {"@type": "MenuItem", "name": it["name"],
                         "offers": {"@type": "Offer", "price": f"{min(vals):.2f}",
                                    "priceCurrency": "CAD"}}
                if it.get("desc") and "PLACEHOLDER" not in it["desc"]:
                    entry["description"] = it["desc"]
                if "veg" in it.get("tags", []):
                    entry["suitableForDiet"] = "https://schema.org/VegetarianDiet"
                items.append(entry)
        if items:
            sections.append({"@type": "MenuSection", "name": c["name"],
                             "description": c.get("blurb", ""), "hasMenuItem": items})
    return {"@type": "Menu", "name": "Tasty Pizza menu", "hasMenuSection": sections}


def topping_art():
    """Reuse the topping drawings already written for the live site rather than
    keeping a second copy of them in sync."""
    js = (ROOT / "src" / "app.js").read_text(encoding="utf-8")
    start = js.index("var TOPPING_LOOK = {")
    return js[start:js.index("\n  };", start) + 5]


def main():
    css = (ROOT / "src" / "brand.css").read_text(encoding="utf-8")
    js = (ROOT / "src" / "brand.js").read_text(encoding="utf-8")
    b = MENU["builder"]
    a = SITE["address"]

    ticker = "".join(f"<span>{t}</span>" for t in TICKER)
    live = [d for d in DEALS["deals"] if d.get("active")][:4]
    deals = "".join(deal_card(d, "Most ordered" if i == 0 else None)
                    for i, d in enumerate(live))
    # six items, exactly one flagged — more flags and none of them register
    cards = "".join(card(n, "Most ordered" if i == 0 else None) for i, n in enumerate(
        ["All Dressed", "Meat Lovers", "Garlic Fingers", "Donair Pizza",
         "Vegetarian", "Classic Poutine"]))

    sizes = "".join(
        f'<button class="chip" type="button" data-size="{i}"{" data-on" if i == 1 else ""}>{s}</button>'
        for i, s in enumerate(b["sizes"]))
    crusts = "".join(
        f'<button class="chip" type="button" data-crust="{c["name"]}" data-sur="{c["surcharge"]}"'
        f'{" data-on" if i == 0 else ""}>{c["name"]}'
        + (f'<em>+{money(c["surcharge"])}</em>' if c["surcharge"] else "") + "</button>"
        for i, c in enumerate(MENU["crusts"]))
    tops = "".join(
        f'<button class="topbtn" type="button" data-top="{t}" aria-pressed="false">'
        f'<i class="tdot" aria-hidden="true"></i>{t}</button>' for t in MENU["toppings"])

    hours = "".join(
        f'<div data-day="{h["day"]}"><dt>{h["day"]}</dt><dd>'
        + ("Closed" if h.get("closed") else
           f'{h["open"] % 12 or 12}{"am" if h["open"] < 12 else "pm"} &ndash; '
           f'{h["close"] % 24 % 12 or 12}{"am" if h["close"] % 24 < 12 else "pm"}')
        + "</dd></div>" for h in SITE["hours"])
    areas = "".join(f"<span>{x}</span>" for x in SITE["delivery"]["areas"])

    lat, lng = SITE["geo"]["lat"], SITE["geo"]["lng"]
    bbox = f"{lng - 0.010},{lat - 0.005},{lng + 0.010},{lat + 0.005}"

    ld = {"@context": "https://schema.org", "@type": "Restaurant", "name": SITE["name"],
          "description": SITE["seo"]["description"], "url": SITE["seo"]["url"],
          "telephone": "+1-902-435-5700", "email": SITE["email"],
          "servesCuisine": ["Pizza", "Donair", "Seafood", "Canadian"], "priceRange": "$$",
          "acceptsReservations": False,
          "address": {"@type": "PostalAddress", "streetAddress": a["street"],
                      "addressLocality": a["city"], "addressRegion": a["province"],
                      "postalCode": a["postal"], "addressCountry": a["country"]},
          "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng},
          "areaServed": [{"@type": "Place", "name": x} for x in SITE["delivery"]["areas"]],
          "openingHoursSpecification": [
              {"@type": "OpeningHoursSpecification", "dayOfWeek": h["day"],
               "opens": f"{h['open']:02d}:00", "closes": f"{h['close'] % 24:02d}:00"}
              for h in SITE["hours"] if not h.get("closed")],
          "hasMenu": menu_schema()}

    build_data = json.dumps({"sizes": b["sizes"], "prices": b["priceByToppingCount"],
                             "max": b["maxToppings"], "special": b["specialName"]},
                            separators=(",", ":"))

    html = f"""<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tasty Pizza &mdash; Pizza, Donairs &amp; Garlic Fingers in Dartmouth, NS</title>
<meta name="description" content="{SITE['seo']['description']}">
<meta name="robots" content="noindex,nofollow">
<link rel="stylesheet" href="https://unpkg.com/lenis@1.3.26/dist/lenis.css">
<style>{css}</style>
<script type="application/ld+json">{json.dumps(ld, separators=(',', ':'))}</script>
</head>
<body>
<a class="skip" href="#order">Skip to ordering</a>

<header class="bar">
  <a class="brand" href="#top"><img src="{IMG}logo-clean.webp"
     srcset="{IMG}logo-clean.webp 414w, {IMG}logo-clean@2x.webp 828w"
     width="414" height="172" alt="Tasty Pizza, Dartmouth"></a>
  <nav><a href="#order">Menu</a><a href="#deals">Deals</a><a href="#build">Build a pizza</a><a href="#find">Find us</a></nav>
  <span class="openpill" data-clock>Open till 11pm</span>
  <a class="btn btn-red btn-sm" href="tel:{SITE['phoneLink']}">902-435-5700</a>
  <button class="dots" type="button" data-sheet-toggle aria-label="Menu" aria-expanded="false"><i></i></button>
</header>

<div class="sheet" data-sheet>
  <a href="#order">See the menu</a>
  <a href="#deals">Deals on right now</a>
  <a href="#build">Build your own pizza</a>
  <a href="#find">Hours &amp; directions</a>
  <a href="mailto:{SITE['email']}">Email us</a>
  <span class="openpill" data-clock>Open till 11pm</span>
</div>

<main id="top">
<section class="hero">
  <div class="wrap">
    <div class="hero-in">
      <div class="hero-copy">
        <p class="eyebrow" data-anim>760 Main Street &middot; Dartmouth</p>
        <h1 class="display" data-anim>Dartmouth&rsquo;s<br><em>pizza.</em></h1>
        <p class="lede" data-anim>Dough and sauce made fresh every morning, hand-stretched, out of
          a deck oven on Main Street. Twenty years in the same spot.</p>
        <div class="acts" data-anim>
          <a class="btn btn-red" href="#order">Start your order</a>
          <a class="btn btn-line" href="tel:{SITE['phoneLink']}">Call 902-435-5700</a>
        </div>
        <p class="hero-facts" data-anim>
          <span><b>20&ndash;30 min</b> pickup</span>
          <span><b>{money(SITE['delivery']['fee'])}</b> delivery</span>
          <span><b>Free</b> parking</span>
        </p>
      </div>

      <figure class="turntable" data-anim="grow">
        <span class="badge"><span><b>2am</b>Friday</span></span>
        <div class="disc disc-spin">
          <img src="{IMG}meat-lovers-pizza.webp" width="800" height="600"
               alt="A pepperoni pizza straight out of the deck oven" fetchpriority="high">
        </div>
        <svg class="orbit" viewBox="0 0 100 100" aria-hidden="true">
          <defs><path id="ring" d="M50,50 m-48.4,0 a48.4,48.4 0 1,1 96.8,0 a48.4,48.4 0 1,1 -96.8,0"/></defs>
          <text><textPath href="#ring" startOffset="0">
            Fresh dough daily &middot; Hand stretched &middot; Deck oven &middot; 760 Main St &middot;
          </textPath></text>
        </svg>
      </figure>
    </div>

    <nav class="quick" data-stagger aria-label="Jump to">
      <a class="qp" href="#order"><img src="{IMG}all-dressed-pizza@sm.webp" width="400" height="300" alt="">
        <span><b>Pizza</b><small>12 to choose from</small></span></a>
      <a class="qp" href="#order"><img src="{IMG}donair@sm.webp" width="400" height="300" alt="">
        <span><b>Donairs</b><small>Six ways</small></span></a>
      <a class="qp" href="#order"><img src="{IMG}garlic-fingers@sm.webp" width="400" height="300" alt="">
        <span><b>Garlic fingers</b><small>With donair sauce</small></span></a>
      <a class="qp is-deal" href="#deals"><span class="qp-mark">%</span>
        <span><b>Deals</b><small>{len(live)} on right now</small></span></a>
    </nav>
  </div>
</section>

<div class="ticker" aria-hidden="true"><div class="ticker-row">{ticker}{ticker}</div></div>

<section class="band" id="deals">
  <div class="wrap">
    <header class="sec-head" data-anim>
      <div><h2 class="sec">Deals on right now</h2>
        <p>Prices before tax. No code needed &mdash; just ask for it.</p></div>
      <a class="btn btn-line btn-sm" href="#order">See the full menu</a>
    </header>
    <div class="deals" data-stagger>{deals}</div>
  </div>
</section>

<section class="band band-paper" id="order">
  <div class="wrap">
    <header class="sec-head" data-anim>
      <div><h2 class="sec">What people actually order</h2>
        <p>The six we make most of. Tap to add, then call or order online.</p></div>
      <a class="btn btn-line btn-sm" href="#">All 152 items</a>
    </header>
    <div class="cards" data-stagger>{cards}</div>
  </div>
</section>

<section class="band" id="build">
  <div class="wrap">
    <header class="sec-head" data-anim>
      <div><h2 class="sec">Build your own</h2>
        <p>Pick a size, tap toppings. The price moves as you go.</p></div>
    </header>
    <div class="build">
      <div class="build-stage">
        <div class="peel">
          <span class="peel-board" aria-hidden="true"></span>
          <div class="dough" data-dough>
            <span class="sauce" aria-hidden="true"></span>
            <span class="cheese" aria-hidden="true"></span>
            <div class="tops" data-tops></div>
          </div>
        </div>
        <p class="readout"><b data-price>$12.90</b><span data-note>12&Prime; Medium &middot; just cheese</span></p>
        <button class="btn btn-red btn-sm" type="button" data-add="Custom pizza">Add to my order</button>
      </div>
      <div class="build-ctrl">
        <div class="ctrl"><h3>Size</h3><div class="chips" data-sizes>{sizes}</div></div>
        <div class="ctrl"><h3>Crust</h3><div class="chips" data-crusts>{crusts}</div></div>
        <div class="ctrl">
          <h3>Toppings <em data-count>0 of {b['maxToppings']}</em></h3>
          <div class="tops-grid" data-topgrid>{tops}</div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="band band-paper">
  <div class="wrap">
    <header class="sec-head" data-anim><h2 class="sec">Ordering is three steps</h2></header>
    <div class="steps" data-stagger>
      <div class="step"><h3>Pick your food</h3>
        <p>Tap anything on the menu to add it to your list. Nothing is charged here.</p></div>
      <div class="step"><h3>Call or order online</h3>
        <p>Read your list to us on the phone, or send it to DoorDash or Uber Eats in one tap.</p></div>
      <div class="step"><h3>Pick up or delivered</h3>
        <p>Twenty to thirty minutes for pickup. {SITE['delivery']['note']}</p></div>
    </div>
  </div>
</section>

<section class="band" id="find">
  <div class="wrap find">
    <div>
      <h2 class="sec" data-anim>Find us</h2>
      <p class="lede" data-anim style="margin-top:.7rem">{a['street']}, {a['note']}.<br>
        {a['city']}, {a['province']} {a['postal']}</p>
      <dl class="hours" data-anim>{hours}</dl>
      <p style="font-size:.92rem;color:var(--ink-2)" data-anim>We deliver to:</p>
      <div class="areas" data-anim>{areas}</div>
      <div class="acts" data-anim>
        <a class="btn btn-red" href="tel:{SITE['phoneLink']}">Call 902-435-5700</a>
        <a class="btn btn-line" href="{SITE['mapsDirectionsUrl']}" target="_blank" rel="noopener">Directions</a>
      </div>
    </div>
    <a class="mapcard" href="{SITE['mapsUrl']}" target="_blank" rel="noopener"
       aria-label="Open Tasty Pizza in Google Maps" data-anim>
      <iframe src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&amp;layer=mapnik&amp;marker={lat},{lng}"
              title="Map of 760 Main Street, Dartmouth" loading="lazy" tabindex="-1" aria-hidden="true"></iframe>
      <span class="pin">Open in Google Maps</span>
      <span class="mapattr">&copy; OpenStreetMap contributors</span>
    </a>
  </div>
</section>
</main>

<nav class="dock" aria-label="Order">
  <a href="#order" class="main">See the menu</a>
  <a href="tel:{SITE['phoneLink']}">Call</a>
</nav>

<script src="https://unpkg.com/lenis@1.3.26/dist/lenis.min.js"></script>
<script>
window.BUILD={build_data};
window.HOURS={json.dumps([{"day": h["day"], "open": h.get("open"), "close": h.get("close"),
                           "closed": h.get("closed", False)} for h in SITE["hours"]],
                         separators=(',', ':'))};
{topping_art()}
</script>
<script>{js}</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    n = sum(len(s["hasMenuItem"]) for s in ld["hasMenu"]["hasMenuSection"])
    print(f"wrote {OUT}")
    print(f"  Menu schema: {len(ld['hasMenu']['hasMenuSection'])} sections, {n} items")


if __name__ == "__main__":
    main()

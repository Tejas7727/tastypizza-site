"""Direction 2 — the ordering experience.

  hero          one locked screen: everything needed to start an order
  order         nine categories -> items -> cart. Never a 150-item list
  build         the pizza toy, pinned on phones
  steps         how ordering works, for people who do not shop online much
  find          hours, areas served, map

    python scripts/brand_study.py   ->  research/_brand-study.html
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "research" / "_brand-study.html"
MENU = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
SITE = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
DEALS = json.loads((ROOT / "data" / "deals.json").read_text(encoding="utf-8"))
NAV = json.loads((ROOT / "data" / "nav.json").read_text(encoding="utf-8"))
PHOTOS = json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8"))["picks"]

IMG = "../assets/img/"

# which categories each running deal belongs inside
DEAL_CATS = {
    "large-4-topping": ["pizza"], "pizza-and-fingers": ["pizza", "garlic-fingers"],
    "two-mediums": ["pizza"], "party-box": ["sides", "chicken"],
    "egg-rolls-6": ["donairs"], "pogos-6": ["donairs"],
    "two-large-subs": ["subs"], "two-can-dine": [],
}


def money(v):
    return f"${v:,.2f}"


def visible(xs):
    return [x for x in xs if not x.get("hidden")]


def all_groups():
    out = {}
    for c in visible(MENU["categories"]):
        for g in c["groups"]:
            out[g["id"]] = g
    return out


def item_json(it, g):
    """One item, flattened for the client: sizes become buttons."""
    sizes = g.get("sizes")
    if "prices" in it:
        prices = it["prices"]
    elif "tier" in it and g.get("tiers"):
        prices = g["tiers"][str(it["tier"])]
    elif "price" in it:
        prices = [it["price"]]
    else:
        prices = [None]
    if sizes and len(prices) > 1:
        rows = [{"label": s, "price": p} for s, p in zip(sizes, prices)]
    else:
        rows = [{"label": "", "price": prices[0]}]
    out = {"name": it["name"], "sizes": rows}
    if it.get("desc") and "PLACEHOLDER" not in it["desc"]:
        out["desc"] = it["desc"]
    if it.get("photo"):
        out["photo"] = it["photo"]
        out["alt"] = PHOTOS.get(it["photo"], {}).get("alt", it["name"])
    if it.get("tags"):
        out["tags"] = it["tags"]
    if it.get("builder"):
        # not a product with a price: a row that opens the configurator
        out["builder"] = True
    return out


def categories_json():
    groups = all_groups()
    out = []
    for c in NAV["categories"]:
        gs = []
        for gid in c["groups"]:
            g = groups.get(gid)
            if not g:
                continue
            items = [item_json(it, g) for it in visible(g["items"])]
            if items:
                gs.append({"name": g["name"], "note": g.get("note", ""), "items": items})
        if gs:
            out.append({"id": c["id"], "name": c["name"], "blurb": c.get("blurb", ""), "groups": gs})
    return out


def menu_schema():
    """Menu schema earns roughly 25% more clicks from search, and it is what AI
    answers and voice assistants read."""
    groups = all_groups()
    sections = []
    for c in NAV["categories"]:
        items = []
        for gid in c["groups"]:
            g = groups.get(gid)
            if not g:
                continue
            for it in visible(g["items"]):
                d = item_json(it, g)
                prices = [s["price"] for s in d["sizes"] if s["price"] is not None]
                if not prices and d.get("builder"):
                    # the configurator's cheapest possible pizza — this row is the
                    # one a search result should carry, so it gets a "from" price
                    prices = [min(MENU["builder"]["priceByToppingCount"][0])]
                if not prices:
                    continue
                e = {"@type": "MenuItem", "name": it["name"],
                     "offers": {"@type": "Offer", "price": f"{min(prices):.2f}",
                                "priceCurrency": "CAD"}}
                if d.get("desc"):
                    e["description"] = d["desc"]
                if "veg" in it.get("tags", []):
                    e["suitableForDiet"] = "https://schema.org/VegetarianDiet"
                items.append(e)
        if items:
            sections.append({"@type": "MenuSection", "name": c["name"],
                             "description": c.get("blurb", ""), "hasMenuItem": items})
    return {"@type": "Menu", "name": "Tasty Pizza menu", "hasMenuSection": sections}


def topping_art():
    """Reuse the topping drawings from the live site instead of keeping a second
    copy in sync. The slice starts at "var TOPPING_LOOK", so that keyword has to
    come off before the object can be hung on window."""
    js = (ROOT / "src" / "app.js").read_text(encoding="utf-8")
    start = js.index("var TOPPING_LOOK = {")
    block = js[start:js.index("\n  };", start) + 5]
    assert block.startswith("var "), block[:20]
    return "window." + block[4:]


def main():
    css = (ROOT / "src" / "brand.css").read_text(encoding="utf-8")
    js = (ROOT / "src" / "brand.js").read_text(encoding="utf-8")
    cfgjs = (ROOT / "src" / "config.js").read_text(encoding="utf-8")
    b = MENU["builder"]
    a = SITE["address"]
    cats = categories_json()
    live = [d for d in DEALS["deals"] if d.get("active")]

    # the nine doors, plus deals as the tenth tile
    tiles = "".join(
        f'<button class="cat" type="button" data-cat="{c["id"]}">'
        f'<img src="{IMG}{next((x["photo"] for x in NAV["categories"] if x["id"] == c["id"]), "")}.webp"'
        f' width="800" height="600" loading="lazy" alt="">'
        f'<span class="cat-in"><b>{c["name"]}</b>'
        f'<small>{sum(len(g["items"]) for g in c["groups"])} to choose from</small></span></button>'
        for c in cats)

    # sizes, crusts and toppings are no longer baked into the page: the
    # configurator renders itself wherever it is opened, and there is now more
    # than one place — the build section, a menu row, a slot inside a deal.
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

    shop = {"img": IMG, "taxRate": SITE["taxRate"], "categories": cats,
            "hours": [{"day": h["day"], "open": h.get("open"), "close": h.get("close"),
                       "closed": h.get("closed", False)} for h in SITE["hours"]],
            "deals": [{"id": d["id"], "name": d["name"], "desc": d.get("desc", ""),
                       "price": d["price"], "compareAt": d.get("compareAt"),
                       "photo": d.get("photo"), "slots": d.get("slots", []),
                       "cats": DEAL_CATS.get(d["id"], [])} for d in live]}
    build_data = {"sizes": b["sizes"], "prices": b["priceByToppingCount"],
                  "max": b["maxToppings"], "special": b["specialName"],
                  "extra": b["extraToppingPrice"]}

    html = f"""<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
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
  <nav><a href="#order">Menu</a><a href="#build">Build a pizza</a><a href="#find">Find us</a></nav>
  <div class="bar-right">
    <span class="openpill" data-clock>Open</span>
    <a class="btn btn-red btn-sm" href="tel:{SITE['phoneLink']}">902-435-5700</a>
    <button class="cartbtn" type="button" data-cart-open hidden aria-label="Your order">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M5 8h14l-1.2 11.2A2 2 0 0 1 15.8 21H8.2a2 2 0 0 1-2-1.8Z"/>
        <path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg><b>0</b></button>
    <button class="dots" type="button" data-sheet-toggle aria-label="Menu" aria-expanded="false"><i></i></button>
  </div>
</header>

<div class="sheet" data-sheet>
  <a href="#order">See the menu</a>
  <a href="#build">Build your own pizza</a>
  <a href="#find">Hours &amp; directions</a>
  <a href="tel:{SITE['phoneLink']}">Call 902-435-5700</a>
  <span class="openpill" data-clock>Open</span>
</div>

<main id="top">
<section class="hero">
  <div class="wrap hero-in">
    <div class="hero-copy">
      <p class="eyebrow" data-anim>760 Main Street &middot; Dartmouth</p>
      <h1 class="display" data-anim>Dartmouth&rsquo;s<br><em>pizza.</em></h1>
      <p class="lede" data-anim>Fresh dough every morning, hand-stretched, out of a deck oven.
        {SITE['owner']}.</p>
    </div>
    <div class="hero-cta">
      <div class="acts" data-anim>
        <a class="btn btn-red" href="#order">Start your order</a>
        <a class="btn btn-line" href="tel:{SITE['phoneLink']}">Call</a>
      </div>
      <p class="hero-facts" data-anim>
        <span><b>20&ndash;30 min</b> pickup</span>
        <span><b>{money(SITE['delivery']['fee'])}</b> delivery</span>
        <span><b>Free</b> parking</span>
      </p>
    </div>
    <figure class="turntable" data-anim="grow">
      <span class="badge"><span><b>1am</b>Fri &amp; Sat</span></span>
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
</section>

<section class="band band-paper order-wrap" id="order">
  <div class="wrap">
    <header class="sec-head" data-order-head>
      <div><h2 class="sec">What are you after?</h2>
        <p>Pick a section &mdash; deals inside it come first.</p></div>
      <span class="openpill" data-clock>Open</span>
    </header>
    <div class="cats" data-cats data-stagger>{tiles}</div>
    <div class="catview" data-catview hidden></div>
  </div>
</section>

<section class="band" id="build">
  <div class="wrap">
    <header class="sec-head" data-anim>
      <div><h2 class="sec">Build your own</h2>
        <p>Pick a size, tap toppings. The price moves as you go.</p></div>
    </header>
    <div data-build-mount></div>
  </div>
</section>

<section class="band band-paper">
  <div class="wrap">
    <header class="sec-head" data-anim><h2 class="sec">Ordering is three steps</h2></header>
    <div class="steps" data-stagger>
      <div class="step"><h3>Pick your food</h3>
        <p>Tap a section, then tap a price. It goes in the basket at the top of the screen.</p></div>
      <div class="step"><h3>Check the basket</h3>
        <p>You see the total with HST before anything else happens. Change your mind freely.</p></div>
      <div class="step"><h3>Pay or call</h3>
        <p>Pay online, or read the order to us on the phone. Twenty to thirty minutes for pickup.</p></div>
    </div>
  </div>
</section>

<section class="band" id="find">
  <div class="wrap find">
    <div>
      <h2 class="sec" data-anim>Find us</h2>
      <p class="lede" data-anim style="margin-top:.6rem">{a['street']}, {a['note']}.<br>
        {a['city']}, {a['province']} {a['postal']}</p>
      <dl class="hours" data-anim>{hours}</dl>
      <p style="font-size:.9rem;color:var(--ink-2)" data-anim>We deliver to:</p>
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

<div class="scrim" data-scrim data-cart-close></div>
<aside class="cart" data-cart aria-label="Your order">
  <div class="cart-head">
    <h2>Your order</h2>
    <button class="x" type="button" data-cart-close aria-label="Close">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2.2" stroke-linecap="round"><path d="m6 6 12 12M18 6 6 18"/></svg></button>
  </div>
  <div class="cart-list" data-cart-list></div>
  <div class="cart-foot" data-cart-foot hidden>
    <div class="tot"><span>Subtotal</span><b data-sub>$0.00</b></div>
    <div class="tot"><span data-taxlabel>HST 14%</span><b data-tax>$0.00</b></div>
    <div class="tot grand"><span>Total</span><b data-total>$0.00</b></div>
    <label class="note-field" data-notefield>
      <span>Anything we should know?</span>
      <textarea data-order-note rows="2" maxlength="280"
        placeholder="Well done, no onions, buzzer is broken &mdash; that sort of thing"></textarea>
    </label>
    <button class="btn btn-red btn-wide" type="button" data-checkout>Checkout</button>
    <div class="pay" data-pay hidden>
      <div class="paynote" data-paynote hidden><b>Your note</b><span data-paynote-text></span></div>
      <div class="paybox">
        <h3>Card payment goes here</h3>
        <p>This is where the payment provider drops in &mdash; Square, Stripe or Moneris. It is
          left as a placeholder on purpose: no card details are collected by this page.</p>
      </div>
      <a class="btn btn-red btn-wide" href="tel:{SITE['phoneLink']}">Call and read your order</a>
      <a class="btn btn-line btn-wide" href="{SITE['ordering']['doordash']}" target="_blank" rel="noopener">Order on DoorDash</a>
      <button class="btn btn-line btn-wide" type="button" data-paydone>Back to the order</button>
    </div>
    <p class="cart-note">Delivery {money(SITE['delivery']['fee'])} on orders over
      {money(SITE['delivery']['minimum'])} after 2pm.</p>
  </div>
</aside>

<script src="https://unpkg.com/lenis@1.3.26/dist/lenis.min.js"></script>
<script>
window.SHOP={json.dumps(shop, separators=(',', ':'))};
window.BUILD={json.dumps(build_data, separators=(',', ':'))};
window.TOPPINGS={json.dumps(MENU["toppings"], separators=(',', ':'))};
window.CRUSTS={json.dumps(MENU["crusts"], separators=(',', ':'))};
{topping_art()}
</script>
<script>{cfgjs}</script>
<script>{js}</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    items = sum(len(g["items"]) for c in cats for g in c["groups"])
    print(f"wrote {OUT}")
    print(f"  {len(cats)} categories, {items} orderable items")
    print(f"  Menu schema: {sum(len(s['hasMenuItem']) for s in ld['hasMenu']['hasMenuSection'])} items")


if __name__ == "__main__":
    main()

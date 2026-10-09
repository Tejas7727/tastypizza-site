"""Build the Tasty Pizza website into docs/.

Everything the site says comes from the JSON files in data/, so the shop edits
those (or the Excel workbook that writes them) and re-runs.

    index.html            the pizza wheel, the category doors, how to find us
    menu.html             the menu: one door per category
    menu/<category>.html  that category's dishes as cards you can order from
    deals.html            every running deal
    build.html            build or customize a pizza, or fill a deal's pizzas
    order.html            the order: lines, special instructions, totals
    about.html, faq.html

Every page is a real page, so the browser's own Back returns a customer to
exactly where they were — the same spot on the category they left.

    python storefront.py        (build.py runs this for you)
"""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

DOCS = ROOT / "docs"
MENU = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
SITE = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
DEALS = json.loads((ROOT / "data" / "deals.json").read_text(encoding="utf-8"))
NAV = json.loads((ROOT / "data" / "nav.json").read_text(encoding="utf-8"))
PHOTOS = json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8"))["picks"]
FAQ_PATH = ROOT / "data" / "faq.json"
FAQ = json.loads(FAQ_PATH.read_text(encoding="utf-8")) if FAQ_PATH.exists() else {"faq": []}
HOME = SITE["home"]

# GitHub Pages serves the site from a sub-path; og: and canonical need the
# full URL, so keep it in one place.
CANON = "https://tejas7727.github.io/tastypizza-site/"

# The preview must not compete with the real tastypizza.ca in search. robots.txt
# stops crawling, but a blocked URL can still be indexed from links, so the page
# says it too. Flip "live" in site.json when the site moves to its own domain.
ROBOTS = "" if SITE.get("live") else '<meta name="robots" content="noindex,nofollow">\n'

# which categories each running deal belongs inside
DEAL_CATS = {
    "large-4-topping": ["pizza"], "pizza-and-fingers": ["pizza", "garlic-fingers"],
    "two-mediums": ["pizza"], "party-box": ["sides", "chicken"],
    "egg-rolls-6": ["donairs"], "pogos-6": ["donairs"],
    "two-large-subs": ["subs"], "two-can-dine": [],
}


def e(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def money(v):
    return f"${v:,.2f}"


def slug(s):
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in s)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def visible(xs):
    return [x for x in xs if not x.get("hidden")]


def all_groups():
    out = {}
    for c in visible(MENU["categories"]):
        for g in c["groups"]:
            out[g["id"]] = g
    return out


def item_json(it, g):
    """One item, flattened: every size becomes a label and a price."""
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
        if len(sizes) == len(MENU["builder"]["sizes"]) and sizes[0].startswith('9"'):
            sizes = MENU["builder"]["sizes"]
        rows = [{"label": s, "price": p} for s, p in zip(sizes, prices)]
    else:
        rows = [{"label": "", "price": prices[0]}]
    out = {"name": it["name"], "sizes": rows, "group": g["id"]}
    if it.get("desc") and "PLACEHOLDER" not in it["desc"]:
        out["desc"] = it["desc"]
    if it.get("photo"):
        out["photo"] = it["photo"]
        out["alt"] = PHOTOS.get(it["photo"], {}).get("alt", it["name"])
        # Cards show the shop's own photos only. Stock pictures of someone
        # else's food are the "unnecessary pictures"; a card without one is
        # cleaner than a card with a fake. Each photo the owner sends shows up.
        if PHOTOS.get(it["photo"], {}).get("real"):
            out["real"] = True
    if it.get("tags"):
        out["tags"] = it["tags"]
    if it.get("builder"):
        out["builder"] = True
    if it.get("addon"):
        out["addon"] = True
    if "addons" in it:
        out["addons"] = it["addons"]
    if "tops" in it:
        out["tops"] = it["tops"]
        out["free"] = it.get("free", 0)
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
                gs.append({"id": g["id"], "name": g["name"], "note": g.get("note", ""),
                           "items": items})
        if gs:
            out.append({"id": c["id"], "name": c["name"], "blurb": c.get("blurb", ""),
                        "photo": c.get("photo"), "groups": gs})
    return out


def menu_schema():
    """Menu schema earns roughly 25% more clicks from search, and it is what AI
    answers and voice assistants read."""
    sections = []
    for c in categories_json():
        items = []
        for g in c["groups"]:
            for d in g["items"]:
                prices = [s["price"] for s in d["sizes"] if s["price"] is not None]
                if not prices and d.get("builder"):
                    prices = [min(MENU["builder"]["priceByToppingCount"][0])]
                if not prices:
                    continue
                m = {"@type": "MenuItem", "name": d["name"],
                     "offers": {"@type": "Offer", "price": f"{min(prices):.2f}",
                                "priceCurrency": "CAD"}}
                if d.get("desc"):
                    m["description"] = d["desc"]
                if "veg" in d.get("tags", []):
                    m["suitableForDiet"] = "https://schema.org/VegetarianDiet"
                items.append(m)
        if items:
            sections.append({"@type": "MenuSection", "name": c["name"],
                             "description": c.get("blurb", ""), "hasMenuItem": items})
    return {"@type": "Menu", "name": "Tasty Pizza menu", "hasMenuSection": sections}


def topping_art():
    """Reuse the topping drawings from the old site instead of keeping a second
    copy in sync. The slice starts at "var TOPPING_LOOK", so that keyword has to
    come off before the object can be hung on window."""
    js = (ROOT / "src" / "app.js").read_text(encoding="utf-8")
    start = js.index("var TOPPING_LOOK = {")
    block = js[start:js.index("\n  };", start) + 5]
    assert block.startswith("var "), block[:20]
    return "window." + block[4:]


def hour(h):
    h = h % 24
    return f"{h % 12 or 12}{'am' if h < 12 else 'pm'}"


def hours_summary():
    """Mon-Thu 11am-11pm style: consecutive days with the same hours merge."""
    out, run = [], []
    for h in SITE["hours"]:
        key = "closed" if h.get("closed") else f"{hour(h['open'])}–{hour(h['close'])}"
        if run and run[-1][1] == key:
            run[-1][0].append(h["day"])
        else:
            run.append([[h["day"]], key])
    for days, key in run:
        label = days[0][:3] if len(days) == 1 else f"{days[0][:3]}–{days[-1][:3]}"
        out.append((label, "Closed" if key == "closed" else key))
    return out


def asset(name, text):
    """Write a shared asset once and return its URL with a content hash, so a
    changed stylesheet is never served stale from a phone's cache."""
    p = DOCS / "assets" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return f"assets/{name}?v={hashlib.sha1(text.encode()).hexdigest()[:8]}"


# --------------------------------------------------------------------- shell

CART_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M5 8h14l-1.2 11.2A2 2 0 0 1 15.8 21H8.2a2 2 0 0 1-2-1.8Z"/>'
            '<path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>')

NAV_LINKS = [("menu", "Menu", "menu.html"), ("deals", "Deals", "deals.html"),
             ("build", "Build a pizza", "build.html"), ("about", "About", "about.html"),
             ("faq", "FAQ", "faq.html")]


def header(R, active):
    nav = "".join(
        f'<a href="{R}{href}"{" aria-current=\"page\"" if key == active else ""}>{label}</a>'
        for key, label, href in NAV_LINKS)
    sheet = "".join(f'<a href="{R}{href}">{label}</a>' for _, label, href in NAV_LINKS)
    return f"""<a class="skip" href="#main">Skip to content</a>
<header class="bar">
  <a class="brand" href="{R}index.html"><img src="{R}assets/img/logo-clean.webp"
     srcset="{R}assets/img/logo-clean.webp 414w, {R}assets/img/logo-clean@2x.webp 828w"
     sizes="92px" width="414" height="172" alt="Tasty Pizza, Dartmouth"></a>
  <nav aria-label="Main">{nav}</nav>
  <div class="bar-right">
    <span class="openpill" data-clock>Open</span>
    <a class="btn btn-red btn-sm callbtn" href="tel:{SITE['phoneLink']}">{SITE['phone']}</a>
    <a class="cartbtn" href="{R}order.html" data-cartbtn aria-label="Your order">{CART_SVG}<b data-count hidden>0</b></a>
    <button class="dots" type="button" data-sheet-toggle aria-label="Menu" aria-expanded="false"><i></i></button>
  </div>
</header>
<div class="sheet" data-sheet>
  {sheet}
  <a href="{R}order.html">Your order</a>
  <a href="tel:{SITE['phoneLink']}">Call {SITE['phone']}</a>
  <span class="openpill" data-clock>Open</span>
</div>"""


# The build page has no footer: it is only the pizza and the Add button.
TOAST = '<div class="toast" data-toast role="status" aria-live="polite" hidden></div>'


def footer(R):
    a = SITE["address"]
    hrs = "".join(f"<div><dt>{d}</dt><dd>{t}</dd></div>" for d, t in hours_summary())
    links = "".join(f'<a href="{R}{href}">{label}</a>' for _, label, href in NAV_LINKS)
    return f"""<footer class="foot">
  <div class="wrap foot-in">
    <div>
      <img src="{R}assets/img/logo-clean.webp" width="414" height="172" alt="Tasty Pizza" class="foot-logo" loading="lazy">
      <p>{e(a['street'])} {e(a['city'])}, {e(a['province'])} {e(a['postal'])}<br>
        <a href="tel:{SITE['phoneLink']}">{SITE['phone']}</a> &middot;
        <a href="mailto:{SITE['email']}">{SITE['email']}</a></p>
    </div>
    <dl class="foot-hours">{hrs}</dl>
    <nav class="foot-links" aria-label="Footer">{links}
      <a href="{R}order.html">Your order</a>
      <a href="{SITE['ordering']['doordash']}" target="_blank" rel="noopener">DoorDash</a>
      <a href="{SITE['ordering']['ubereats']}" target="_blank" rel="noopener">Uber Eats</a></nav>
  </div>
  <p class="wrap foot-fine">{e(SITE['owner'])}.</p>
</footer>
{TOAST}"""


def page(path, *, title, desc, body, active="", page_id, data=None, ld=None, ASSETS=None):
    depth = path.count("/")
    R = "../" * depth
    canon = CANON + ("" if path == "index.html" else path)
    data_js = ""
    if data:
        data_js = "<script>" + "\n".join(
            f"window.{k}={json.dumps(v, separators=(',', ':'), ensure_ascii=False)};"
            if not isinstance(v, str) or not v.startswith("window.") else v
            for k, v in data.items()) + "</script>\n"
    ld_tag = (f'<script type="application/ld+json">{json.dumps(ld, separators=(",", ":"), ensure_ascii=False)}</script>\n'
              if ld else "")
    html = f"""<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{e(desc)}">
{ROBOTS}<link rel="canonical" href="{canon}">
<meta property="og:type" content="restaurant">
<meta property="og:site_name" content="Tasty Pizza">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{CANON}assets/img/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{CANON}assets/img/og.jpg">
<link rel="icon" href="{R}assets/img/favicon.svg" type="image/svg+xml">
<link rel="preload" href="{R}assets/fonts/archivo-800.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{R}{ASSETS['css']}">
{ld_tag}</head>
<body data-page="{page_id}" data-root="{R}">
{header(R, active)}
<main id="main">
{body}
</main>
{footer(R) if page_id != "build" else TOAST}
{data_js}<script src="https://unpkg.com/lenis@1.3.26/dist/lenis.min.js" defer></script>
{f'<script src="{R}{ASSETS["config"]}" defer></script>' if page_id == "build" else ""}
<script src="{R}{ASSETS['js']}" defer></script>
</body></html>
"""
    out = DOCS / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


# --------------------------------------------------------------------- pieces

def img_tag(R, photo, alt, cls="", sizes="(max-width:640px) 96px, 112px", lazy=True):
    return (f'<img class="{cls}" src="{R}assets/img/{photo}@sm.webp" '
            f'srcset="{R}assets/img/{photo}@sm.webp 400w, {R}assets/img/{photo}.webp 800w" '
            f'sizes="{sizes}" width="400" height="300" alt="{e(alt)}"'
            f'{" loading=\"lazy\"" if lazy else ""}>')


def tiles(R, cats):
    """The category doors. Pizza first and biggest, because it is a pizza shop."""
    by = {c["id"]: c for c in cats}
    b = MENU["builder"]
    pizza = by.get("pizza")
    first = []
    if pizza:
        first.append(("Specialty pizzas", f"{R}menu/pizza.html", pizza["photo"],
                      f'{sum(len(g["items"]) for g in pizza["groups"])} to choose from', "is-wide"))
    first.append(("Build your own", f"{R}build.html", "custom-pizza",
                  f"from {money(min(b['priceByToppingCount'][0]))}", ""))
    first.append(("Deals", f"{R}deals.html", "two-topping-pizza",
                  f"{len([d for d in DEALS['deals'] if d.get('active')])} running", "is-deal"))
    rest = [(c["name"], f"{R}menu/{c['id']}.html", c["photo"],
             f'{sum(len(g["items"]) for g in c["groups"])} to choose from', "")
            for c in cats if c["id"] != "pizza"]

    # A door is a tall window: the food fills it, the name sits at the foot.
    # The shop's own photo when there is one, otherwise the category picture.
    def tile(name, href, photo, small, cls):
        img = (f'<img src="{R}assets/img/{photo}@sm.webp" srcset="{R}assets/img/{photo}@sm.webp 400w, '
               f'{R}assets/img/{photo}.webp 800w" sizes="(max-width:620px) 50vw, 240px" '
               f'width="400" height="300" loading="lazy" alt="">' if photo else "")
        return (f'<a class="tile {cls}{"" if photo else " no-photo"}" href="{href}">{img}'
                f'<span class="tile-text"><b>{e(name)}</b><small>{e(small)}</small></span></a>')

    return (f'<h2 class="sec">Pizza</h2><div class="tiles tiles-pizza">'
            + "".join(tile(*t) for t in first) + "</div>"
            + f'<h2 class="sec">Everything else</h2><div class="tiles">'
            + "".join(tile(*t) for t in rest) + "</div>")


def pricebox(d, uid):
    """The price, top right of the card. One price is just the price; several
    sizes are a box showing the smallest that opens into every size."""
    priced = [(i, x) for i, x in enumerate(d["sizes"]) if x["price"] is not None]
    if len(priced) == 1:
        return f'<div class="pbox is-fixed"><b>{money(priced[0][1]["price"])}</b></div>'
    i0, s0 = priced[0]
    opts = "".join(
        f'<li><button type="button" role="option" data-i="{i}" data-price="{x["price"]}" '
        f'data-note="{e(x["label"])}" aria-selected="{"true" if i == i0 else "false"}">'
        f'<span>{e(x["label"])}</span><b>{money(x["price"])}</b></button></li>' for i, x in priced)
    return (f'<div class="pbox" data-szpick>'
            f'<button type="button" class="pbox-btn" aria-haspopup="listbox" aria-expanded="false" '
            f'aria-controls="{uid}-sz" aria-label="Size: {e(s0["label"])}, {money(s0["price"])}. Change size">'
            f'<small data-szlabel>{e(s0["label"])}</small><b data-szprice>{money(s0["price"])}</b>'
            f'<i class="caret" aria-hidden="true"></i></button>'
            f'<ul class="pbox-menu" id="{uid}-sz" role="listbox" aria-label="Sizes" hidden>{opts}</ul></div>')


def card_top(R, name, box, tags, desc, img):
    return (f'<div class="card-top"><h3>{e(name)}</h3>{box}'
            f'<div class="card-text">{f"<div class=card-tags>{tags}</div>" if tags else ""}'
            f'{f"<p>{e(desc)}</p>" if desc else ""}</div>{img}</div>')


def stepper():
    return ('<div class="stepper" data-stepper><button type="button" data-step="-1" aria-label="One fewer">&minus;</button>'
            '<output data-qty>1</output><button type="button" data-step="1" aria-label="One more">+</button></div>')


def addon_boxes(d, addons):
    """Cheese and extra meat as tick boxes on the dish itself, priced for the
    size picked, instead of separate cards nobody connects to their donair."""
    allowed = [a for a in addons if a["name"] in d.get("addons", [a["name"] for a in addons])]
    if not allowed:
        return ""
    boxes = "".join(
        f'<label class="addon"><input type="checkbox" data-addon="{e(a["name"].removeprefix("Add ").lower())}" '
        f'data-prices="{e(json.dumps([x["price"] for x in a["sizes"]]))}">'
        f'<span>+ {e(a["name"].removeprefix("Add "))} <b data-addon-price>{money(a["sizes"][0]["price"])}</b></span></label>'
        for a in allowed)
    return f'<div class="addons">{boxes}</div>'


def card(R, d, cat_id, addons=()):
    """A dish you can order without opening anything: pick a size from the
    price box, set a quantity, Add. Specialty pizzas also get Customize."""
    uid = slug(d["group"] + "-" + d["name"])
    tags = "".join({"veg": '<span class="tag tag-veg">Veg</span>',
                    "popular": '<span class="tag">Most ordered</span>'}.get(t, "")
                   for t in d.get("tags", []))
    img = img_tag(R, d["photo"], d.get("alt", d["name"]), "card-img") if d.get("real") else ""

    if d.get("builder"):
        b = MENU["builder"]
        box = f'<div class="pbox is-fixed"><small>from</small><b>{money(min(b["priceByToppingCount"][0]))}</b></div>'
        return (f'<article class="card card-build" id="{uid}">'
                f'{card_top(R, d["name"], box, tags, d.get("desc"), img)}'
                f'<div class="card-foot"><a class="btn btn-red btn-sm" href="{R}build.html">Build it</a></div></article>')

    priced = [s for s in d["sizes"] if s["price"] is not None]
    if not priced:
        box = '<div class="pbox is-fixed"><small>Ask</small></div>'
        return (f'<article class="card" id="{uid}">{card_top(R, d["name"], box, tags, d.get("desc"), img)}'
                f'<div class="card-foot"><a class="btn btn-line btn-sm" href="tel:{SITE["phoneLink"]}">Call</a></div></article>')

    start = priced[0]
    custom = ""
    if d["group"] == "gourmet":
        idx = d["sizes"].index(start)
        key = quote(f'{d["group"]}/{d["name"]}')
        custom = (f'<a class="btn btn-line btn-sm" href="{R}build.html?item={key}&amp;size={idx}"'
                  f' data-customize>Customize</a>')
    return (f'<article class="card" id="{uid}" data-card data-name="{e(d["name"])}">'
            f'{card_top(R, d["name"], pricebox(d, uid), tags, d.get("desc"), img)}'
            f'{addon_boxes(d, addons)}'
            f'<div class="card-foot">{stepper()}'
            f'{custom}<button class="btn btn-red btn-sm btn-add" type="button" data-add'
            f' data-base="{start["price"]}" data-price="{start["price"]}" data-note="{e(start["label"])}">Add '
            f'<span data-total>{money(start["price"])}</span></button></div></article>')


def deal_card(R, d):
    was = d.get("compareAt") and d["compareAt"] > d["price"]
    box = (f'<div class="pbox is-fixed is-deal"><b>{money(d["price"])}</b>'
           + (f'<s>{money(d["compareAt"])}</s>' if was else "") + '</div>')
    tags = '<span class="tag tag-deal">Deal</span>' + (
        f'<span class="tag tag-save">Save {money(d["compareAt"] - d["price"])}</span>' if was else "")
    real = PHOTOS.get(d.get("photo") or "", {}).get("real")
    img = img_tag(R, d["photo"], "", "card-img") if real else ""
    top = card_top(R, d["name"], box, tags, d.get("desc", ""), img)
    if d.get("slots"):
        n = len([s for s in d["slots"] if s["type"] == "pizza"])
        return (f'<article class="card card-deal" id="deal-{d["id"]}">{top}<div class="card-foot">'
                f'<a class="btn btn-red btn-sm" href="{R}build.html?deal={d["id"]}">'
                f'{"Choose your pizzas" if n > 1 else "Choose your toppings"}</a></div></article>')
    return (f'<article class="card card-deal" id="deal-{d["id"]}" data-card data-name="{e(d["name"])}">{top}'
            f'<div class="card-foot">{stepper()}'
            f'<button class="btn btn-red btn-sm btn-add" type="button" data-add data-price="{d["price"]}"'
            f' data-note="deal">Add <span data-total>{money(d["price"])}</span></button></div></article>')


def rail(R, cats, active):
    pills = "".join(
        f'<a class="pill" href="{R}menu/{c["id"]}.html"{" aria-current=\"page\"" if c["id"] == active else ""}>'
        f'{e(c["name"])}</a>' for c in cats)
    return (f'<nav class="rail" aria-label="Categories"><div class="wrap rail-in">'
            f'<a class="rail-back" href="{R}menu.html" aria-label="All of the menu"><i></i></a>'
            f'<div class="rail-track" data-rail>{pills}'
            f'<a class="pill" href="{R}deals.html"{" aria-current=\"page\"" if active == "deals" else ""}>Deals</a>'
            f'</div></div></nav>')


def find_us(R):
    a = SITE["address"]
    lat, lng = SITE["geo"]["lat"], SITE["geo"]["lng"]
    bbox = f"{lng - 0.010},{lat - 0.005},{lng + 0.010},{lat + 0.005}"
    hours = "".join(
        f'<div data-day="{h["day"]}"><dt>{h["day"]}</dt><dd>'
        + ("Closed" if h.get("closed") else f'{hour(h["open"])} &ndash; {hour(h["close"])}')
        + "</dd></div>" for h in SITE["hours"])
    areas = "".join(f"<span>{e(x)}</span>" for x in SITE["delivery"]["areas"])
    return f"""<section class="band" id="find">
  <div class="wrap find">
    <div>
      <h2 class="sec">Find us</h2>
      <p class="lede">{e(a['street'])}, {e(a['note'])}.<br>{e(a['city'])}, {e(a['province'])} {e(a['postal'])}</p>
      <dl class="hours">{hours}</dl>
      <p class="small">We deliver to:</p>
      <div class="areas">{areas}</div>
      <div class="acts">
        <a class="btn btn-red" href="tel:{SITE['phoneLink']}">Call {SITE['phone']}</a>
        <a class="btn btn-line" href="{SITE['mapsDirectionsUrl']}" target="_blank" rel="noopener">Directions</a>
      </div>
    </div>
    <a class="mapcard" href="{SITE['mapsUrl']}" target="_blank" rel="noopener" aria-label="Open Tasty Pizza in Google Maps">
      <iframe src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&amp;layer=mapnik&amp;marker={lat},{lng}"
              title="Map of 760 Main Street, Dartmouth" loading="lazy" tabindex="-1" aria-hidden="true"></iframe>
      <span class="pin">Open in Google Maps</span>
      <span class="mapattr">&copy; OpenStreetMap contributors</span>
    </a>
  </div>
</section>"""


def faq_entries():
    """Answers built from the shop's own data, so an hours or price change in
    the spreadsheet changes the FAQ too, plus anything the shop writes itself."""
    b, d, a = MENU["builder"], SITE["delivery"], SITE["address"]
    hrs = "; ".join(f"{day} {t}" for day, t in hours_summary())
    gf = next((c for c in MENU["crusts"] if "glutenfree" in c.get("tags", [])), None)
    others = [c["name"] for c in MENU["crusts"] if c is not gf]
    gourmet = all_groups().get("gourmet", {"items": []})
    veg = [it["name"] for it in visible(gourmet["items"]) if "veg" in it.get("tags", [])]
    pickup = next((f"{bold} {rest}" for bold, rest in HOME.get("facts", []) if rest == "pickup"), "")
    out = [
        ("What are your hours?", f"{hrs}. Hours can change on holidays, so call {SITE['phone']} if you are unsure."),
        ("Do you deliver?", f"Yes, to {', '.join(d['areas'][:-1])} and {d['areas'][-1]}. "
                            f"{d['note']} The delivery charge is {money(d['fee'])}."),
        ("Where are you?", f"{a['street']} in {a['city']}, {a['note'].lower()}. Parking is free."),
        ("How do I order?", f"Put your order together on this site, then call it in on {SITE['phone']} "
                            "or order through DoorDash or Uber Eats."),
        ("How does build your own work?", f"Pick a size and tap toppings — a {b['sizes'][1]} with cheese is "
                                          f"{money(b['priceByToppingCount'][0][1])}, and {b['maxToppings']} toppings "
                                          f"makes it a {b['specialName']}. You can add more past that; the price of "
                                          "each extra one shows as you go."),
    ]
    if gf:
        out.append(("Do you have gluten-free crust?",
                    f"Yes, gluten-free crust is +{money(gf['surcharge'])}. "
                    f"{' and '.join(others)} crust {'costs' if len(others) == 1 else 'cost'} nothing extra."))
    if veg:
        out.append(("What vegetarian pizzas do you have?",
                    f"{', '.join(veg[:-1])} and {veg[-1]}, plus any pizza you build yourself."))
    if pickup:
        out.append(("How long does pickup take?", f"About {pickup.replace(' pickup', '')}."))
    for q in FAQ.get("faq", []):
        if q.get("q") and q.get("a"):
            out.append((q["q"], q["a"]))
    return out


# --------------------------------------------------------------------- pages

def main():
    cats = categories_json()
    b = MENU["builder"]
    live = [d for d in DEALS["deals"] if d.get("active")]

    css = (ROOT / "src" / "tasty.css").read_text(encoding="utf-8")
    js = (ROOT / "src" / "tasty.js").read_text(encoding="utf-8")
    cfgjs = (ROOT / "src" / "config.js").read_text(encoding="utf-8")
    ASSETS = {"css": asset("tasty.css", css), "js": asset("tasty.js", js),
              "config": asset("config.js", cfgjs)}
    common = {"SHOP": {"taxRate": SITE["taxRate"],
                       "hours": [{"day": h["day"], "open": h.get("open"), "close": h.get("close"),
                                  "closed": h.get("closed", False)} for h in SITE["hours"]]}}
    a = SITE["address"]
    restaurant = {
        "@context": "https://schema.org", "@type": "Restaurant", "name": SITE["name"],
        "description": SITE["seo"]["description"], "url": SITE["seo"]["url"],
        "telephone": "+1-902-435-5700", "email": SITE["email"],
        "servesCuisine": ["Pizza", "Donair", "Seafood", "Canadian"], "priceRange": "$$",
        "address": {"@type": "PostalAddress", "streetAddress": a["street"],
                    "addressLocality": a["city"], "addressRegion": a["province"],
                    "postalCode": a["postal"], "addressCountry": a["country"]},
        "geo": {"@type": "GeoCoordinates", "latitude": SITE["geo"]["lat"], "longitude": SITE["geo"]["lng"]},
        "areaServed": [{"@type": "Place", "name": x} for x in SITE["delivery"]["areas"]],
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": h["day"],
             "opens": f"{h['open']:02d}:00", "closes": f"{h['close'] % 24:02d}:00"}
            for h in SITE["hours"] if not h.get("closed")],
        "hasMenu": menu_schema()}

    # ---------------- home
    wide, phone = HOME["sloganWide"], HOME["sloganPhone"]
    slogan = (f'<span class="wide">{"".join(f"{e(x)}<br>" for x in wide[:-1])}</span>'
              f'<span class="narrow">{"".join(f"{e(x)}<br>" for x in phone[:-1])}</span>'
              f'<em>{e(wide[-1])}</em>')
    facts = "".join(f"<span><b>{e(x)}</b> {e(y)}</span>" for x, y in HOME["facts"])

    # What slides across the home page. Any running deal with a "homePie" (set
    # from the Deals sheet) rides, in the sheet's order; then the vegetarian;
    # then the builder. Every slide is a link to the page that sells it.
    slides = []
    for d in live:
        if d.get("homePie"):
            slides.append({"pie": d["homePie"], "kick": "Tonight’s deal", "name": d["name"],
                           "desc": d.get("desc", ""), "price": d["price"], "was": d.get("compareAt"),
                           "href": f"build.html?deal={d['id']}" if d.get("slots") else f"deals.html#deal-{d['id']}",
                           "cta": ("See the deal" if not d.get("slots") else "Choose your pizzas"
                                   if sum(x["type"] == "pizza" for x in d["slots"]) > 1 else "Choose your toppings")})
    gourmet = all_groups().get("gourmet")
    veg = next((it for it in gourmet["items"] if it["name"] == "Vegetarian"), None) if gourmet else None
    if veg:
        slides.append({"pie": "veggie", "kick": "Made without meat", "cls": "is-green",
                       "name": veg["name"], "desc": veg.get("desc", ""),
                       "price": gourmet["tiers"][str(veg["tier"])][1], "unit": gourmet["sizes"][1],
                       "href": f"menu/pizza.html#{slug('gourmet-' + veg['name'])}", "cta": "See it on the menu"})
    slides.append({"pie": "build-your-own", "kick": "Make it yours", "cls": "is-grey",
                   "name": b["specialName"], "build": True, "href": "build.html", "cta": "Build it now",
                   "desc": f'Pick your size, tap {b["maxToppings"]} toppings, watch it land.',
                   "price": b["priceByToppingCount"][b["maxToppings"]][1], "unit": b["sizes"][1]})
    # Only the first pizza loads with the page; the rest sit stacked in the
    # first screen, where loading="lazy" would fetch them all at once.
    pies = "".join(
        f'<div class="disc{" is-cur" if not i else ""}">'
        + (f'<img src="assets/img/pie-{s["pie"]}.webp" fetchpriority="high"' if not i else
           f'<img data-src="assets/img/pie-{s["pie"]}.webp"')
        + f' width="680" height="680" alt="{e(s["name"])}"></div>'
        for i, s in enumerate(slides))

    home = f"""<section class="hero">
  <div class="wrap hero-in">
    <div class="hero-copy">
      <p class="eyebrow">{e(HOME['eyebrow'])}</p>
      <h1 class="display">{slogan}</h1>
      <p class="lede">{e(HOME['lede'])}</p>
    </div>
    <div class="hero-cta">
      <div class="acts">
        <a class="btn btn-red" href="menu.html">Start your order</a>
        <a class="btn btn-line" href="tel:{SITE['phoneLink']}">Call</a>
      </div>
      <p class="hero-facts">{facts}</p>
    </div>
    <div class="herofig">
      <div class="stage">
      <div class="turntable" data-wheelstage tabindex="0" role="group"
           aria-roledescription="carousel" aria-label="Tonight&rsquo;s offers">
        <div class="pieclip" aria-hidden="true"><div class="pies">{pies}</div></div>
        <div class="orbit" aria-hidden="true">
          <svg viewBox="0 0 360 360">
            <defs><path id="ring" d="M180,180 m-147,0 a147,147 0 1,1 294,0 a147,147 0 1,1 -294,0"/></defs>
            <g><text><textPath href="#ring" startOffset="0">
              Fresh dough daily &middot; Hand stretched &middot; Deck oven &middot; 760 Main St &middot;
            </textPath></text></g>
          </svg>
        </div>
        <span class="badge" data-badge aria-hidden="true">
          <i data-badge-kick>Deal</i><b data-badge-price>&nbsp;</b><s data-badge-was></s></span>
      </div>
      </div>
      <div class="ticks" data-ticks role="tablist" aria-label="Choose an offer"></div>
      <a class="deal" data-deal href="menu.html" aria-live="polite">
        <div class="dealin">
          <p class="kicker" data-kicker>Tonight&rsquo;s deal</p>
          <h2 data-dealname>&nbsp;</h2>
          <p class="sub" data-dealdesc>&nbsp;</p>
          <p class="saveline"><span class="was" data-dealwas hidden></span>
            <span class="save" data-dealsave hidden></span></p>
          <span class="dealgo" data-dealcta>See it on the menu</span>
        </div>
      </a>
    </div>
  </div>
</section>
<section class="band band-tiles">
  <div class="wrap">
    <header class="pagehead"><h2 class="sec-big">What are you after?</h2></header>
    {tiles("", cats)}
  </div>
</section>
{find_us("")}"""
    page("index.html", title="Tasty Pizza &mdash; Pizza, Donairs &amp; Garlic Fingers in Dartmouth, NS",
         desc=SITE["seo"]["description"], body=home, page_id="home", ASSETS=ASSETS,
         data={**common, "SLIDES": slides}, ld=restaurant)

    # ---------------- menu
    menu_body = f"""<section class="band">
  <div class="wrap">
    <header class="pagehead"><h1 class="sec-big">The menu</h1>
      <p>Pick a section. Every dish can be ordered straight from its card.</p></header>
    {tiles("", cats)}
  </div>
</section>"""
    page("menu.html", title="Menu &mdash; Tasty Pizza, Dartmouth",
         desc="Pizza, donairs, garlic fingers, subs, wings, seafood, burgers and poutine from Tasty Pizza on Main Street, Dartmouth.",
         body=menu_body, active="menu", page_id="menu", ASSETS=ASSETS, data=common)

    # ---------------- one page per category
    for c in cats:
        offers = [d for d in live if c["id"] in DEAL_CATS.get(d["id"], [])]
        body = rail("../", cats, c["id"]) + f'<section class="band band-menu"><div class="wrap">'
        body += (f'<header class="pagehead"><h1 class="sec-big">{e(c["name"])}</h1>'
                 f'{f"<p>{e(c[chr(98)+chr(108)+chr(117)+chr(114)+chr(98)])}</p>" if c.get("blurb") else ""}</header>')
        if offers:
            body += ('<h2 class="grouphead">Deals on these</h2><div class="cards cards-strip">'
                     + "".join(deal_card("../", d) for d in offers) + "</div>")
        for g in c["groups"]:
            body += (f'<h2 class="grouphead" id="{g["id"]}">{e(g["name"])}</h2>'
                     + (f'<p class="groupnote">{e(g["note"])}</p>' if g.get("note") else "")
                     + '<div class="cards">' + "".join(card("../", d, c["id"], [a for a in g["items"] if a.get("addon")])
                                                     for d in g["items"] if not d.get("addon")) + "</div>")
        body += "</div></section>"
        page(f"menu/{c['id']}.html", title=f"{e(c['name'])} &mdash; Tasty Pizza, Dartmouth",
             desc=(f"{c['name']} at Tasty Pizza, 760 Main St., Dartmouth. "
                   + (c.get("blurb") or "") + f" Pickup or delivery, call {SITE['phone']}.")[:160],
             body=body, active="menu", page_id="category", ASSETS=ASSETS, data=common)

    # ---------------- deals
    deals_body = (rail("", cats, "deals")
                  + '<section class="band band-menu"><div class="wrap">'
                  + '<header class="pagehead"><h1 class="sec-big">Deals</h1>'
                  + '<p>Running now. Pizza deals let you pick every topping.</p></header>'
                  + '<div class="cards">' + "".join(deal_card("", d) for d in live) + "</div></div></section>")
    page("deals.html", title="Deals &mdash; Tasty Pizza, Dartmouth",
         desc="Pizza deals and combos at Tasty Pizza on Main Street, Dartmouth: pick every topping, pickup or delivery.",
         body=deals_body, active="deals", page_id="category", ASSETS=ASSETS, data=common)

    # ---------------- build / customize
    pizzas = {}
    for c in cats:
        if c["id"] != "pizza":
            continue
        for g in c["groups"]:
            for d in g["items"]:
                if d["group"] == "gourmet":
                    pizzas[f'{d["group"]}/{d["name"]}'] = {
                        "name": d["name"], "desc": d.get("desc", ""),
                        "prices": [s["price"] for s in d["sizes"]],
                        "tops": d.get("tops", []), "free": d.get("free", 0)}
    build_body = f"""<section class="band band-build">
  <div class="wrap">
    <a class="backlink" href="menu/pizza.html" data-back>Back</a>
    <header class="pagehead build-head">
      <h1 class="sec-big" data-build-title>Build your own pizza</h1>
      <p data-build-sub>Pick a size and crust, then tap toppings. The price moves as you go.</p>
    </header>
    <div class="build-grid">
      <div class="build-steps" data-steps></div>
      <aside class="summary" data-summary aria-label="Your pizza">
        <div class="summary-pie">
          <div class="peel"><span class="peel-board" aria-hidden="true"></span>
            <div class="dough" data-dough><span class="sauce"></span><span class="cheese"></span>
              <div class="tops" data-tops></div></div></div>
        </div>
        <div class="summary-text">
          <p class="summary-which" data-which hidden></p>
          <dl class="summary-lines" data-lines></dl>
          <p class="summary-price"><span>Total</span><b data-price>$0.00</b></p>
        </div>
        <div class="summary-foot">
          <div class="stepper" data-buildqty><button type="button" data-step="-1" aria-label="One fewer">&minus;</button>
            <output data-qty>1</output><button type="button" data-step="1" aria-label="One more">+</button></div>
          <button class="btn btn-red" type="button" data-build-add>Add to order</button>
        </div>
      </aside>
    </div>
  </div>
</section>"""
    page("build.html", title="Build a pizza &mdash; Tasty Pizza, Dartmouth",
         desc="Build your own pizza at Tasty Pizza, Dartmouth: pick a size and crust, tap toppings, and watch the price as you go.",
         body=build_body, active="build", page_id="build", ASSETS=ASSETS,
         data={**common,
               "BUILD": {"sizes": b["sizes"], "prices": b["priceByToppingCount"], "max": b["maxToppings"],
                         "special": b["specialName"], "extra": b["extraToppingPrice"],
                         # extra cheese and the special toppings, each priced by size
                         "specials": [{"name": "Extra Cheese", "prices": next(
                                          it["prices"] for it in all_groups()["pizza-extras"]["items"]
                                          if it["name"] == "Extra Cheese")}]
                                     + [{"name": n, "prices": MENU["specialToppings"]["prices"]}
                                        for n in MENU["specialToppings"]["names"]]},
               "TOPPINGS": MENU["toppings"], "CRUSTS": MENU["crusts"],
               "DEALS": {d["id"]: {"name": d["name"], "desc": d.get("desc", ""), "price": d["price"],
                                   "slots": d.get("slots", [])} for d in live if d.get("slots")},
               "PIZZAS": pizzas, "TOPPING_LOOK": topping_art()})

    # ---------------- order
    order_body = f"""<section class="band band-order">
  <div class="wrap">
    <a class="backlink" href="menu.html" data-back>Keep ordering</a>
    <header class="pagehead"><h1 class="sec-big">Your order</h1></header>
    <div class="order-empty" data-empty hidden>
      <p>Nothing here yet.</p>
      <a class="btn btn-red" href="menu.html">Browse the menu</a>
    </div>
    <div class="order-grid" data-full hidden>
      <div>
        <ul class="lines" data-lines></ul>
        <label class="note-field" for="order-note"><span>Anything we should know?</span>
          <textarea id="order-note" data-order-note rows="3" maxlength="280"
            placeholder="Well done, no onions, buzzer is broken &mdash; that sort of thing"></textarea></label>
      </div>
      <aside class="totals" aria-label="Totals">
        <div class="tot"><span>Subtotal</span><b data-sub>$0.00</b></div>
        <div class="tot"><span data-taxlabel>HST</span><b data-tax>$0.00</b></div>
        <div class="tot grand"><span>Total</span><b data-total>$0.00</b></div>
        <button class="btn btn-red btn-wide" type="button" data-checkout>Checkout</button>
        <div class="pay" data-pay hidden>
          <div class="paynote" data-paynote hidden><b>Your note</b><span data-paynote-text></span></div>
          <div class="paybox"><h3>Online payment is coming</h3>
            <p>Until it is switched on, read this order to us on the phone, or order the same
              things through DoorDash or Uber Eats.</p></div>
          <a class="btn btn-red btn-wide" href="tel:{SITE['phoneLink']}">Call {SITE['phone']}</a>
          <a class="btn btn-line btn-wide" href="{SITE['ordering']['doordash']}" target="_blank" rel="noopener">Order on DoorDash</a>
          <a class="btn btn-line btn-wide" href="{SITE['ordering']['ubereats']}" target="_blank" rel="noopener">Order on Uber Eats</a>
        </div>
        <p class="small">{e(SITE['delivery']['note'])} Delivery is {money(SITE['delivery']['fee'])}.</p>
      </aside>
    </div>
  </div>
</section>"""
    page("order.html", title="Your order &mdash; Tasty Pizza, Dartmouth",
         desc="Your Tasty Pizza order: check it, add special instructions, then call it in or order for pickup or delivery.", body=order_body, page_id="order", ASSETS=ASSETS, data=common)

    # ---------------- about
    latest = max(h['close'] for h in SITE['hours'] if not h.get('closed'))
    late_days = [h['day'] for h in SITE['hours'] if not h.get('closed') and h['close'] == latest]
    about_body = f"""<section class="band">
  <div class="wrap narrowcol">
    <header class="pagehead"><h1 class="sec-big">{e(SITE['tagline'])}</h1></header>
    <div class="prose">
      <p>Tasty Pizza is on {e(a['street'])} in {e(a['city'])}, {e(a['note'].lower())}.
        {e(SITE['owner'])}.</p>
      <p>The dough is made fresh every morning and stretched by hand, and the pizzas go
        into a deck oven. Garlic fingers come with donair sauce, and the donairs are the
        Halifax kind, carved off the spit.</p>
      <p>We are open seven days, till {hour(latest)} on {e(' and '.join(late_days))},
        and we deliver to {e(', '.join(SITE['delivery']['areas']))}.</p>
    </div>
    <div class="acts"><a class="btn btn-red" href="menu.html">See the menu</a>
      <a class="btn btn-line" href="tel:{SITE['phoneLink']}">Call {SITE['phone']}</a></div>
  </div>
</section>
{find_us("")}"""
    page("about.html", title="About &mdash; Tasty Pizza, Dartmouth",
         desc=f"{SITE['tagline']}. {SITE['owner']}.", body=about_body, active="about",
         page_id="about", ASSETS=ASSETS, data=common, ld=restaurant)

    # ---------------- faq
    qa = faq_entries()
    faq_body = (f'<section class="band"><div class="wrap narrowcol">'
                f'<header class="pagehead"><h1 class="sec-big">Questions</h1></header>'
                + '<div class="faq">' + "".join(
                    f'<details><summary>{e(q)}</summary><p>{e(an)}</p></details>' for q, an in qa)
                + f'</div><p class="small">Something else? Call <a href="tel:{SITE["phoneLink"]}">{SITE["phone"]}</a>.</p>'
                  f'</div></section>')
    page("faq.html", title="FAQ &mdash; Tasty Pizza, Dartmouth",
         desc="Hours, delivery areas, crusts and how ordering works at Tasty Pizza, Dartmouth.",
         body=faq_body, active="faq", page_id="faq", ASSETS=ASSETS, data=common,
         ld={"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
             {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": an}}
             for q, an in qa]})

    n = sum(len(g["items"]) for c in cats for g in c["groups"])
    print(f"wrote {len(cats) + 7} pages: index, menu, {len(cats)} categories, deals, build, order, about, faq")
    print(f"  {n} orderable items, {len(live)} live deals, {len(qa)} FAQ answers")
    print(f"  Menu schema: {sum(len(s['hasMenuItem']) for s in restaurant['hasMenu']['hasMenuSection'])} items")


if __name__ == "__main__":
    main()

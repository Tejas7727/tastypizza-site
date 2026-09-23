#!/usr/bin/env python3
"""Shared helpers and page chrome for the Tasty Pizza build.

    python build.py

Nothing here needs installing. Standard library only.
Everything the site says comes from the JSON files in data/ - change those, re-run this,
and the site updates. The GitHub Action does exactly that on every push.
"""
import json, re, shutil, html
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = ROOT / "src"
OUT = ROOT / "docs"

# ---------------------------------------------------------------- data helpers

def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def money(v):
    return f"${v:,.2f}" if v is not None else "Call for price"


def e(s):
    return html.escape(str(s), quote=True)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def visible(items):
    return [i for i in items if not i.get("hidden")]


def item_prices(item, group):
    """Resolve an item's price list, following a group's price tiers if it uses them."""
    if "prices" in item:
        return item["prices"]
    if "tier" in item and group.get("tiers"):
        return group["tiers"][str(item["tier"])]
    if "price" in item:
        return [item["price"]]
    return [None]


def from_price(item, group):
    vals = [p for p in item_prices(item, group) if p is not None]
    return min(vals) if vals else None


# ---------------------------------------------------------------- components

def icon(name):
    p = {
        "phone": '<path d="M4 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L14 13l5 2v4a2 2 0 0 1-2.2 2A16 16 0 0 1 2 6.2 2 2 0 0 1 4 4Z"/>',
        "pin": '<path d="M12 21s7-6.3 7-11a7 7 0 1 0-14 0c0 4.7 7 11 7 11Z"/><circle cx="12" cy="10" r="2.6"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.2l3.3 2"/>',
        "bag": '<path d="M5 8h14l-1 12H6L5 8Z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
        "search": '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
        "plus": '<path d="M12 6v12M6 12h12"/>',
        "minus": '<path d="M6 12h12"/>',
        "x": '<path d="m6 6 12 12M18 6 6 18"/>',
        "chev": '<path d="m9 6 6 6-6 6"/>',
        "parking": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M10 16V9h3a2.5 2.5 0 0 1 0 5h-3"/>',
        "card": '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/>',
        "dough": '<circle cx="12" cy="12" r="8"/><path d="M9 10h.01M15 11h.01M12 15h.01"/>',
        "star": '<path d="m12 4 2.3 4.9 5.2.7-3.8 3.7.9 5.3-4.6-2.6-4.6 2.6.9-5.3L4.5 9.6l5.2-.7Z"/>',
        "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    }.get(name, "")
    return (f'<svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{p}</svg>')


def photo_tag(slug, alt, cls="", sizes="(max-width:700px) 92vw, 380px", lazy=True):
    if not slug:
        return ""
    return (f'<img class="{cls}" src="assets/img/{slug}.webp" '
            f'srcset="assets/img/{slug}@sm.webp 400w, assets/img/{slug}.webp 800w" '
            f'sizes="{sizes}" width="800" height="600" alt="{e(alt)}"'
            f'{" loading=\"lazy\" decoding=\"async\"" if lazy else ""}>')


def add_button(name, price, label="Add"):
    """Every add-to-tray control on the site is one of these."""
    return (f'<button class="add" type="button" data-add="{e(name)}" data-price="{price if price is not None else ""}">'
            f'{icon("plus")}<span>{label}</span></button>')


# ---------------------------------------------------------------- page chrome

def hours_json(site):
    """Hours as data the page's clock can read. 26 means 2am the next day."""
    return json.dumps([{"day": h["day"], "open": h.get("open"), "close": h.get("close"),
                        "closed": h.get("closed", False)} for h in site["hours"]])


def topbar(site, page):
    nav = [("index.html", "Home"), ("menu.html", "Menu"),
           ("index.html#deals", "Deals"), ("index.html#find", "Find us")]
    links = "".join(
        f'<a href="{h}"{" class=\"on\"" if (page == "menu" and h == "menu.html") or (page == "home" and h == "index.html") else ""}>{t}</a>'
        for h, t in nav)
    return f"""
<header class="top">
  <a class="brand" href="index.html" aria-label="Tasty Pizza, home">
    <img src="assets/img/logo.webp" width="421" height="179" alt="Tasty Pizza">
  </a>
  <nav class="nav">{links}</nav>
  <div class="top-act">
    <span class="openpill" data-clock hidden></span>
    <a class="btn btn-ghost tel" href="tel:{site['phoneLink']}">{icon('phone')}<span>{site['phone']}</span></a>
    <a class="btn btn-red" href="{'#order' if page == 'home' else 'index.html#order'}">{icon('bag')}<span>Order</span></a>
  </div>
  <button class="burger" type="button" aria-label="Menu" aria-expanded="false"><span></span><span></span><span></span></button>
</header>
<div class="drawer" hidden>
  <nav>{links}</nav>
  <a class="btn btn-red big" href="tel:{site['phoneLink']}">{icon('phone')}Call {site['phone']}</a>
</div>"""


def footer(site):
    a = site["address"]
    areas = ", ".join(site["delivery"]["areas"])
    hrs = "".join(
        f'<div class="hrow" data-day="{h["day"]}"><dt>{h["day"]}</dt><dd>'
        + ("Closed" if h.get("closed") else f'{fmt_hour(h["open"])} – {fmt_hour(h["close"])}')
        + "</dd></div>" for h in site["hours"])
    fine = "".join(f"<li>{e(f)}</li>" for f in site["finePrint"])
    return f"""
<footer class="foot">
  <div class="foot-grid">
    <div>
      <img class="foot-logo" src="assets/img/logo.webp" width="421" height="179" alt="Tasty Pizza">
      <p class="foot-blurb">{e(site['blurb'])}</p>
      <div class="foot-social">
        <a href="{site['social']['facebook']}" rel="noopener">Facebook</a>
        <a href="{site['social']['instagram']}" rel="noopener">Instagram</a>
      </div>
    </div>
    <div>
      <h3>Find us</h3>
      <p><a class="ul" href="{site['mapsUrl']}" target="_blank" rel="noopener">{e(a['street'])}<br>{e(a['note'])}<br>{e(a['city'])}, {e(a['province'])} {e(a['postal'])}</a></p>
      <p><a class="ul" href="tel:{site['phoneLink']}">{site['phone']}</a><br>
         <a class="ul" href="mailto:{site['email']}">{site['email']}</a></p>
    </div>
    <div>
      <h3>Hours</h3>
      <dl class="hours">{hrs}</dl>
    </div>
    <div>
      <h3>Delivery</h3>
      <p>{e(site['delivery']['note'])} Minimum {money(site['delivery']['minimum'])}, {money(site['delivery']['fee'])} delivery charge.</p>
      <p class="muted">{e(areas)}</p>
    </div>
  </div>
  <ul class="fine">{fine}</ul>
  <p class="credit">Food photography and the hero clip are freely-licensed stock, used as
     placeholders until Tasty Pizza's own photos replace them. Hero clip by Ruth Hartnup
     (<a class="ul" href="https://commons.wikimedia.org/wiki/File:Bubbling_baking_pizza.webm"
     rel="noopener" target="_blank">CC BY 2.0</a>). Map &copy; OpenStreetMap contributors.</p>
  <p class="copy">© {date.today().year} Tasty Pizza. Site rebuilt {date.today().strftime('%B %Y')}.</p>
</footer>"""


def fmt_hour(h):
    if h is None:
        return ""
    hh = h % 24
    suffix = "am" if hh < 12 else "pm"
    disp = hh % 12 or 12
    return f"{disp}{suffix}"


def tray():
    return """
<div class="tray" data-tray hidden>
  <button class="tray-bar" type="button" data-tray-toggle>
    <span class="tray-count" data-tray-count>0</span>
    <span class="tray-label">Your order</span>
    <span class="tray-total" data-tray-total>$0.00</span>
  </button>
  <div class="tray-scrim" data-tray-scrim hidden></div>
  <div class="tray-sheet" data-tray-sheet hidden>
    <div class="tray-head">
      <h2>Your order</h2>
      <button class="iconbtn" type="button" data-tray-close aria-label="Close">
        <svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="m6 6 12 12M18 6 6 18"/></svg>
      </button>
    </div>
    <ul class="tray-list" data-tray-list></ul>
    <div class="tray-sum">
      <span>Total before tax</span><strong data-tray-total>$0.00</strong>
    </div>
    <p class="tray-note">This is a list to read out or send — it doesn't place the order. Pick how you'd like to order:</p>
    <div class="tray-acts" data-tray-acts></div>
    <button class="linkbtn" type="button" data-tray-clear>Clear the list</button>
  </div>
</div>"""


def page(title, desc, body, site, page_id, extra_head="", extra_js=""):
    a = site["address"]
    ld = {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": site["name"],
        "description": site["seo"]["description"],
        "url": site["seo"]["url"],
        "telephone": "+1-902-435-5700",
        "email": site["email"],
        "image": site["seo"]["url"].rstrip("/") + "/assets/img/donair@wide.webp",
        "servesCuisine": ["Pizza", "Donair", "Seafood", "Canadian"],
        "priceRange": "$$",
        "menu": site["seo"]["url"].rstrip("/") + "/menu.html",
        "acceptsReservations": False,
        "address": {"@type": "PostalAddress", "streetAddress": a["street"],
                    "addressLocality": a["city"], "addressRegion": a["province"],
                    "postalCode": a["postal"], "addressCountry": a["country"]},
        "geo": {"@type": "GeoCoordinates", "latitude": site["geo"]["lat"], "longitude": site["geo"]["lng"]},
        "sameAs": [site["social"]["facebook"], site["social"]["instagram"]],
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": h["day"],
             "opens": f"{h['open']:02d}:00", "closes": f"{h['close'] % 24:02d}:00"}
            for h in site["hours"] if not h.get("closed")
        ],
    }
    og = site["seo"]["url"].rstrip("/") + "/assets/img/og.jpg"
    return f"""<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{'' if site.get("live") else '<meta name="robots" content="noindex,nofollow">'}
<link rel="canonical" href="{site['seo']['url'].rstrip('/')}/{'' if page_id == 'home' else page_id + '.html'}">
<meta property="og:type" content="restaurant">
<meta property="og:site_name" content="{e(site['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{og}">
<meta property="og:url" content="{site['seo']['url']}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{og}">
<meta name="theme-color" content="#B70017">
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="assets/img/icon-180.png">
<link rel="preload" href="assets/fonts/alfaslabone-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/archivo-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/site.css">
{extra_head}
<script type="application/ld+json">{json.dumps(ld, separators=(',', ':'))}</script>
</head>
<body data-page="{page_id}">
<a class="skip" href="#main">Skip to content</a>
{topbar(site, page_id)}
<main id="main">
{body}
</main>
{footer(site)}
{tray()}
<div class="callbar">
  <a class="cb cb-red" href="tel:{site['phoneLink']}">{icon('phone')}Call to order</a>
  <a class="cb" href="menu.html">{icon('bag')}Menu</a>
</div>
<script>window.HOURS={hours_json(site)};window.SITE={json.dumps({
    'phone': site['phone'], 'phoneLink': site['phoneLink'], 'email': site['email'],
    'doordash': site['ordering']['doordash'], 'ubereats': site['ordering']['ubereats'],
    'name': site['name']}, separators=(',', ':'))};</script>
<script src="assets/app.js" defer></script>
{extra_js}
</body>
</html>
"""

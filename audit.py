#!/usr/bin/env python3
"""Check the built site for the things that quietly break restaurant websites.

    python audit.py

Exits non-zero if anything FAILs, so the GitHub Action refuses to publish a broken
build. Standard library only.
"""
import json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"
DATA = ROOT / "data"

fails, warns = [], []


def fail(m):
    fails.append(m)


def warn(m):
    warns.append(m)


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.imgs, self.links, self.ids = [], [], []
        self.h1 = 0
        self.title = None
        self.in_title = False
        self.meta = {}
        self.ld = []
        self.in_ld = False
        self.iframes = []
        self.buttons = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "img":
            self.imgs.append(a)
        elif tag == "iframe":
            self.iframes.append(a)
        elif tag == "a" and a.get("href"):
            self.links.append(a)
        elif tag == "h1":
            self.h1 += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "button":
            self.buttons += 1
        elif tag == "meta":
            k = a.get("name") or a.get("property")
            if k:
                self.meta[k] = a.get("content", "")
        elif tag == "link":
            if a.get("rel") == "canonical":
                self.meta["canonical"] = a.get("href", "")
        elif tag == "script" and a.get("type") == "application/ld+json":
            self.in_ld = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "script":
            self.in_ld = False

    def handle_data(self, d):
        if self.in_title:
            self.title = (self.title or "") + d
        if self.in_ld:
            self.ld.append(d)


def check_page(name):
    p = OUT / name
    if not p.exists():
        fail(f"{name} was not built")
        return None
    html = p.read_text(encoding="utf-8")
    s = Scan()
    s.feed(html)
    kb = len(html.encode()) / 1024

    # --- the basics that the old site got wrong -------------------------
    if s.h1 != 1:
        fail(f"{name}: {s.h1} <h1> elements (must be exactly 1)")
    t = (s.title or "").strip()
    if not t:
        fail(f"{name}: no <title>")
    elif len(t) > 65:
        warn(f"{name}: title is {len(t)} chars, Google truncates around 60")
    d = s.meta.get("description", "")
    if not d:
        fail(f"{name}: no meta description")
    elif not (70 <= len(d) <= 165):
        warn(f"{name}: meta description is {len(d)} chars (aim 70-165)")
    for k in ("og:title", "og:description", "og:image", "twitter:card"):
        if not s.meta.get(k):
            fail(f"{name}: missing {k} — shared links will have no preview")
    if not s.meta.get("canonical"):
        fail(f"{name}: no canonical link")

    # --- the phone number must be tappable ------------------------------
    tels = [a for a in s.links if a["href"].startswith("tel:")]
    if not tels:
        fail(f"{name}: no tel: link — the phone number is not tappable")
    mails = [a for a in s.links if a["href"].startswith("mailto:")]
    if name == "index.html" and not mails:
        fail(f"{name}: no mailto: link")

    # --- ordering + map -------------------------------------------------
    if name == "index.html":
        hrefs = " ".join(a["href"] for a in s.links)
        for host, label in (("doordash.com", "DoorDash"), ("ubereats.com", "Uber Eats")):
            if host not in hrefs:
                warn(f"{name}: no {label} link")
        if "google.com/maps" not in hrefs:
            fail(f"{name}: no Google Maps link")

    # --- images ---------------------------------------------------------
    for img in s.imgs:
        src = img.get("src", "")
        if img.get("alt") is None:
            fail(f"{name}: <img src={src}> has no alt attribute")
        if src and not src.startswith(("http", "data:")):
            f = OUT / src
            if not f.exists():
                fail(f"{name}: image not found -> {src}")
        if not (img.get("width") and img.get("height")):
            warn(f"{name}: <img src={src}> has no width/height (causes layout shift)")
        for s2 in re.findall(r"([^\s,]+\.webp)", img.get("srcset", "")):
            if not (OUT / s2).exists():
                fail(f"{name}: srcset image not found -> {s2}")

    # --- internal links and fragments ------------------------------------
    for a in s.links:
        h = a["href"]
        if h.startswith(("http", "tel:", "mailto:", "#")):
            if h.startswith("#") and len(h) > 1 and h[1:] not in s.ids:
                fail(f"{name}: link to #{h[1:]} but nothing on the page has that id")
            continue
        target, _, frag = h.partition("#")
        if target and not (OUT / target).exists():
            fail(f"{name}: dead link -> {target}")

    # --- structured data --------------------------------------------------
    if not s.ld:
        fail(f"{name}: no JSON-LD — Google can't show hours, menu or price range")
    for blob in s.ld:
        try:
            j = json.loads(blob)
        except Exception as err:
            fail(f"{name}: JSON-LD is not valid JSON ({err})")
            continue
        for k in ("name", "address", "telephone", "openingHoursSpecification"):
            if k not in j:
                fail(f"{name}: JSON-LD missing {k}")

    # --- weight ------------------------------------------------------------
    if kb > 200:
        warn(f"{name}: {kb:.0f} KB of HTML")
    print(f"  {name}: {kb:.0f} KB, {len(s.imgs)} images, {len(s.links)} links, {s.buttons} buttons")
    return s


def check_data():
    menu = json.loads((DATA / "menu.json").read_text(encoding="utf-8"))
    photos = json.loads((DATA / "photos.json").read_text(encoding="utf-8"))["picks"]
    deals = json.loads((DATA / "deals.json").read_text(encoding="utf-8"))

    used, placeholders, no_price = set(), [], []
    for c in menu["categories"]:
        for g in c["groups"]:
            for it in g["items"]:
                if it.get("photo"):
                    used.add(it["photo"])
                    if it["photo"] not in photos:
                        fail(f"menu.json: {it['name']} wants photo '{it['photo']}' which has no entry in photos.json")
                if "PLACEHOLDER" in (it.get("desc") or ""):
                    placeholders.append(it["name"])
                ps = it.get("prices") or ([it["price"]] if "price" in it else [])
                if "tier" not in it and not any(p is not None for p in ps):
                    no_price.append(it["name"])
    for d in deals["deals"]:
        if d.get("active") and d.get("photo"):
            used.add(d["photo"])
            if d["photo"] not in photos:
                fail(f"deals.json: '{d['name']}' wants photo '{d['photo']}' which has no entry in photos.json")
        if d.get("compareAt") and d["compareAt"] <= d.get("price", 0):
            warn(f"deals.json: '{d['name']}' compareAt is not above its price, so it shows no saving")

    unused = sorted(set(photos) - used)
    if unused:
        warn(f"{len(unused)} photos built but never used: {', '.join(unused[:8])}"
             + (" ..." if len(unused) > 8 else ""))
    if placeholders:
        warn(f"PLACEHOLDER copy still on the site: {', '.join(placeholders)}")
    if no_price:
        warn(f"items with no price (show as 'Call for price'): {', '.join(no_price)}")

    # real vs stock photography — the number the client should watch
    real = ROOT / "assets" / "photos-in"
    n_real = len([f for f in real.glob("*") if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]) if real.exists() else 0
    print(f"  photos: {len(used)} in use, {n_real} are real Tasty Pizza photos, "
          f"{len(used) - n_real} still stock")


def check_assets():
    for f in ("assets/site.css", "assets/app.js", "assets/img/logo.webp",
              "assets/img/chef.png", "assets/img/favicon.svg", "assets/img/og.jpg",
              ".nojekyll", "robots.txt", "sitemap.xml"):
        if not (OUT / f).exists():
            fail(f"missing build output: {f}")
    css = (OUT / "assets" / "site.css")
    if css.exists():
        text = css.read_text(encoding="utf-8")
        # a class the stylesheet promises but nothing uses is a silent no-op
        # app.js builds some markup at runtime, so it counts as usage too
        sources = ("index.html", "menu.html", "assets/app.js")
        html = " ".join((OUT / p).read_text(encoding="utf-8")
                        for p in sources if (OUT / p).exists())
        for cls in re.findall(r"\.([a-z][a-z0-9-]{3,})\s*\{", text):
            if f'class="{cls}"' not in html and f"{cls} " not in html and f'"{cls}"' not in html:
                if cls not in html:
                    warn(f"CSS defines .{cls} but no element uses it")


def main():
    print("auditing docs/ ...")
    check_assets()
    check_page("index.html")
    check_page("menu.html")
    check_data()
    print()
    for w in warns:
        print(f"WARN  {w}")
    for f in fails:
        print(f"FAIL  {f}")
    print(f"\n{len(fails)} failures, {len(warns)} warnings")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

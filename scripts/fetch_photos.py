"""Pull freely-licensed food photos into research/photo-candidates/.

Wikimedia Commons first (better food photography, and it actually knows what a donair is),
Openverse CC0 as a backstop. Every file's licence and author is recorded in candidates.json
so scripts/credits.py can emit a proper attribution page.

    python scripts/fetch_photos.py                 # every slug that has no candidates yet
    python scripts/fetch_photos.py donair poutine  # just these
    python scripts/fetch_photos.py --force donair  # re-fetch even if files exist
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "research" / "photo-candidates"
UA = "TastyPizzaSiteBuild/1.0 (https://tastypizza.ca; tastypizzadm@gmail.com)"
COMMONS = "https://commons.wikimedia.org/w/api.php"
OPENVERSE = "https://api.openverse.org/v1/images/"
PER_SLUG = 8

QUERIES = {
    "donair":            ["donair", "doner kebab sandwich", "gyro sandwich pita"],
    "donair-pizza":      ["donair pizza", "kebab pizza"],
    "donair-plate":      ["donair platter", "kebab plate fries"],
    "donair-egg-roll":   ["egg roll fried food", "spring roll plate"],
    "donair-pogo":       ["corn dog", "corndog"],
    "donair-poutine":    ["donair poutine", "poutine meat"],
    "garlic-fingers":    ["garlic fingers", "cheesy bread sticks", "garlic cheese bread"],
    "cheese-pizza":      ["cheese pizza", "margherita pizza whole"],
    "all-dressed-pizza": ["supreme pizza", "pizza with many toppings"],
    "meat-lovers-pizza": ["pepperoni pizza", "meat pizza sausage"],
    "veggie-pizza":      ["vegetarian pizza", "vegetable pizza"],
    "greek-pizza":       ["greek pizza feta", "pizza feta olives"],
    "hawaiian-pizza":    ["hawaiian pizza", "pizza pineapple ham"],
    "bbq-chicken-pizza": ["barbecue chicken pizza", "chicken pizza"],
    "poutine":           ["poutine", "french fries gravy cheese curds"],
    "fish-and-chips":    ["fish and chips", "fried haddock chips"],
    "chicken-wings":     ["chicken wings", "buffalo wings plate"],
    "nachos":            ["nachos", "loaded nachos cheese"],
    "burrito":           ["burrito", "chicken burrito wrap"],
    "tacos":             ["tacos", "soft tacos plate"],
    "quesadilla":        ["quesadilla", "cheese quesadilla"],
    "rice-bowl":         ["burrito bowl", "rice bowl chicken"],
    "cold-cut-sub":      ["submarine sandwich", "sub sandwich"],
    "steak-sub":         ["cheesesteak sandwich", "steak sandwich"],
    "hamburger":         ["hamburger and fries", "cheeseburger"],
    "onion-rings":       ["onion rings", "fried onion rings"],
    "mozza-sticks":      ["mozzarella sticks", "fried cheese sticks"],
    "fries":             ["french fries", "chips fries basket"],
    "chicken-fingers":   ["chicken fingers", "chicken tenders fries"],
    "fried-chicken":     ["fried chicken", "fried chicken plate"],
    "salad":             ["garden salad", "caesar salad bowl"],
    "lasagna":           ["lasagna", "lasagne plate"],
    "scallops":          ["fried scallops", "scallops plate"],
    "shrimp":            ["fried shrimp", "shrimp basket"],
    "seafood-platter":   ["seafood platter", "fried seafood plate"],
    "club-sandwich":     ["club sandwich", "club sandwich fries"],
    "pita-wrap":         ["chicken wrap", "shawarma wrap"],
    "bread-sticks":      ["breadsticks", "bread sticks parmesan"],
    "fried-pepperoni":   ["fried pepperoni", "salami snack fried"],
    "pizza-sub":         ["pizza sub sandwich", "hot sub sandwich"],
}

BAD = ("logo", "icon", "map", "diagram", "sign", "poster", "chart", "portrait",
       "restaurant exterior", "storefront", "building")


def get(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40)


def commons(query, limit=10):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrlimit": limit, "gsrnamespace": 6,
        "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1400,
    })
    try:
        with get(COMMONS + "?" + q) as r:
            data = json.load(r)
    except Exception as e:
        print(f"    ! commons failed: {e}")
        return []
    out = []
    for p in (data.get("query", {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl") or ii.get("width", 0) < 800:
            continue
        title = p.get("title", "")
        if any(b in title.lower() for b in BAD):
            continue
        em = ii.get("extmetadata", {})
        lic = (em.get("LicenseShortName", {}).get("value") or "").strip()
        if "nc" in lic.lower().replace("nc-", "nc ").split() or "NonCommercial" in lic:
            continue
        out.append({
            "url": ii["thumburl"],
            "title": title.replace("File:", ""),
            "creator": strip_html(em.get("Artist", {}).get("value", "")),
            "license": lic,
            "source": ii.get("descriptionurl"),
            "provider": "wikimedia",
        })
    return out


def openverse(query, limit=10):
    q = urllib.parse.urlencode({
        "q": query, "license": "cc0,pdm", "page_size": limit,
        "aspect_ratio": "wide", "size": "medium,large", "mature": "false",
    })
    try:
        with get(OPENVERSE + "?" + q) as r:
            rows = json.load(r).get("results", [])
    except Exception:
        return []
    return [{
        "url": x["url"], "title": x.get("title"), "creator": x.get("creator"),
        "license": x.get("license"), "source": x.get("foreign_landing_url"),
        "provider": x.get("provider"),
    } for x in rows if x.get("url")]


def strip_html(s):
    out, skip = [], False
    for ch in s:
        if ch == "<":
            skip = True
        elif ch == ">":
            skip = False
        elif not skip:
            out.append(ch)
    return "".join(out).strip()[:120]


def download(url, dest):
    try:
        with get(url) as r:
            data = r.read()
    except Exception:
        return False
    if len(data) < 20000:
        return False
    dest.write_bytes(data)
    return True


def main():
    force = "--force" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    OUT.mkdir(parents=True, exist_ok=True)
    mf = OUT / "candidates.json"
    manifest = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}

    for slug in (only or list(QUERIES)):
        d = OUT / slug
        d.mkdir(exist_ok=True)
        if force:
            for f in d.glob("*.jpg"):
                f.unlink()
            manifest.pop(slug, None)
        have = len(list(d.glob("*.jpg")))
        if have >= PER_SLUG:
            print(f"{slug}: have {have}, skip")
            continue
        print(f"{slug}:")
        rows, seen, n = manifest.get(slug, []), set(), have
        for q in QUERIES[slug]:
            if n >= PER_SLUG:
                break
            for r in commons(q) + (openverse(q) if n < 3 else []):
                if n >= PER_SLUG:
                    break
                if r["url"] in seen:
                    continue
                seen.add(r["url"])
                dest = d / f"{n:02d}.jpg"
                if download(r["url"], dest):
                    r["file"] = dest.name
                    r["query"] = q
                    rows.append(r)
                    n += 1
                    safe = str(r["title"])[:48].encode("ascii", "replace").decode()
                    print(f"    + {dest.name} [{r['license']}] {safe}")
            time.sleep(0.3)
        manifest[slug] = rows
        mf.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        if n == 0:
            print("    ! nothing found")
    mf.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"\nwrote {mf}")


if __name__ == "__main__":
    main()

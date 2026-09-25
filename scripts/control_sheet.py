"""The Excel control sheet: the shop's way into the website.

    python scripts/control_sheet.py export    data/*.json  ->  TastyPizza-Control.xlsx
    python scripts/control_sheet.py import    TastyPizza-Control.xlsx  ->  data/*.json
    python scripts/control_sheet.py import --dry-run      say what would change

WHY IT WORKS THIS WAY

Export builds the workbook from the JSON, so the sheet always opens showing
exactly what the live site says today.

Import does NOT rewrite the JSON from the sheet. It walks the sheet row by row
and sets individual values in the file that is already there. Everything the
sheet does not cover — the notes, the hidden flags, the deal slots, the photo
choices, the topping list — survives untouched. That matters: a spreadsheet
that rebuilt these files from scratch would quietly delete anything it did not
have a column for.

Every row carries an id in a locked grey column. That id is how a row finds its
way back to the right item; if it is edited or deleted, that row is skipped and
reported rather than guessed at.
"""
import json
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BOOK = ROOT / "TastyPizza-Control.xlsx"

INK = "111113"
RED = "B70017"
GREEN = "0B5C3F"
GREY = "6B6B73"

H_FILL = PatternFill("solid", fgColor=INK)
H_FONT = Font(name="Aptos", bold=True, color="FFFFFF", size=11)
LOCK_FILL = PatternFill("solid", fgColor="EFEFF1")
LOCK_FONT = Font(name="Aptos", color=GREY, size=9)
EDIT_FONT = Font(name="Aptos", size=11)
NOTE_FONT = Font(name="Aptos", italic=True, color=GREY, size=10)
TITLE_FONT = Font(name="Aptos", bold=True, size=16, color=INK)
RED_FONT = Font(name="Aptos", bold=True, size=11, color=RED)
THIN = Side(style="thin", color="D8D8DC")
EDGE = Border(bottom=THIN)


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def save(name, obj):
    (DATA / f"{name}.json").write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sheet(wb, title, intro, headers, widths, locked=0):
    ws = wb.create_sheet(title)
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws["A2"] = intro
    ws["A2"].font = NOTE_FONT
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(len(headers), 4))
    ws.row_dimensions[2].height = 30
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=4, column=i, value=h)
        c.fill, c.font = H_FILL, H_FONT
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 26
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A5"
    ws._locked_cols = locked
    return ws


def row(ws, r, values, locked=0):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=r, column=i, value=v)
        c.border = EDGE
        if i <= locked:
            c.fill, c.font = LOCK_FILL, LOCK_FONT
        else:
            c.font = EDIT_FONT
            c.alignment = Alignment(wrap_text=True, vertical="top")


def yesno(ws, col, first, last):
    dv = DataValidation(type="list", formula1='"yes,no"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(f"{col}{first}:{col}{last}")


# --------------------------------------------------------------------- export

def export():
    site, menu, deals = load("site"), load("menu"), load("deals")
    wb = Workbook()
    wb.remove(wb.active)

    # ---- Start here ----
    ws = wb.create_sheet("Start here")
    ws.column_dimensions["A"].width = 104
    lines = [
        ("Tasty Pizza — website control sheet", TITLE_FONT),
        ("", None),
        ("This workbook is the website. Change something here, publish, and the live "
         "site follows.", EDIT_FONT),
        ("", None),
        ("HOW TO PUBLISH", RED_FONT),
        ("1.  Change what you want on any of the sheets. Save the file (Ctrl+S).", EDIT_FONT),
        ('2.  Close Excel. It has to be closed or the file stays locked.', EDIT_FONT),
        ('3.  Double-click "Publish website" in the same folder as this file.', EDIT_FONT),
        ("4.  A black window opens and tells you what it is doing. When it says DONE, "
         "the site is live in about a minute.", EDIT_FONT),
        ("", None),
        ("WHAT EACH SHEET IS FOR", RED_FONT),
        ("Home page      the big slogan, the sentence under it, the three little facts", EDIT_FONT),
        ("Deals          your offers: turn them on and off, change the price or the wording", EDIT_FONT),
        ("Menu           every dish, its description and its prices", EDIT_FONT),
        ("Pizza builder  what a build-your-own pizza costs, and extra toppings", EDIT_FONT),
        ("Hours          opening and closing times", EDIT_FONT),
        ("Shop details   phone, email, delivery fee, tax, DoorDash and Uber Eats links", EDIT_FONT),
        ("", None),
        ("THE GREY COLUMNS", RED_FONT),
        ("Grey columns are how each row finds its way back to the website. Do not edit "
         "them, do not delete rows, do not sort the sheet. Everything else is yours.", EDIT_FONT),
        ("", None),
        ("IF SOMETHING LOOKS WRONG", RED_FONT),
        ("Nothing goes live if a price is not a number or a required box is empty — the "
         "window will say which row and nothing will be published. Fix it and run it again.",
         EDIT_FONT),
    ]
    for i, (text, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=text)
        if font:
            c.font = font
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if i > 2:
            ws.row_dimensions[i].height = 18 if text else 8

    # ---- Home page ----
    home = site["home"]
    ws = sheet(wb, "Home page",
               "The words on the front of the website. The LAST line of each slogan is the "
               "one printed in red. The phone slogan is shown on phones, where three lines "
               "take up too much of the screen — keep it to two short lines.",
               ["What", "Line", "Text"], [26, 8, 74], locked=2)
    r = 5
    for key, label in (("sloganWide", "Slogan (laptop)"), ("sloganPhone", "Slogan (phone)")):
        for i, line in enumerate(home[key]):
            row(ws, r, [f"home.{key}", i + 1, line], locked=2)
            r += 1
    row(ws, r, ["home.eyebrow", 1, home["eyebrow"]], locked=2); r += 1
    row(ws, r, ["home.lede", 1, home["lede"]], locked=2); r += 1
    for i, (bold, rest) in enumerate(home["facts"]):
        row(ws, r, ["home.facts", i + 1, f"{bold} | {rest}"], locked=2)
        r += 1
    ws.cell(row=r + 1, column=3,
            value='Facts are written as  bold part | the rest  — e.g.  Free | parking').font = NOTE_FONT

    # ---- Deals ----
    ws = sheet(wb, "Deals",
               "Your offers. \"Showing\" turns one on or off on the website — no need to "
               "delete it. \"Was price\" is the crossed-out price; leave it empty for no "
               "saving. Prices are numbers only, no dollar sign.",
               ["id", "Showing", "Name", "Description", "Price", "Was price"],
               [22, 11, 34, 52, 11, 11], locked=1)
    r = 5
    for d in deals["deals"]:
        row(ws, r, [d["id"], "yes" if d.get("active") else "no", d["name"],
                    d.get("desc", ""), d.get("price"), d.get("compareAt")], locked=1)
        r += 1
    yesno(ws, "B", 5, r - 1)

    # ---- Menu ----
    ws = sheet(wb, "Menu",
               "Every dish on the site. Change a name, a description or any price. Prices "
               "are numbers only. Leave a price empty if that size is not sold. Items "
               "priced by a shared tier show their tier's prices — changing one changes "
               "every dish on that tier, which is how the printed menu works.",
               ["id", "Section", "Dish", "Description",
                "Price 1", "Price 2", "Price 3", "Price 4", "Sizes"],
               [30, 22, 26, 46, 10, 10, 10, 10, 22], locked=1)
    r = 5
    for c in menu["categories"]:
        for g in c["groups"]:
            sizes = g.get("sizes") or []
            for it in g["items"]:
                if "prices" in it:
                    prices = list(it["prices"])
                elif "price" in it:
                    prices = [it["price"]]
                elif "tier" in it:
                    prices = list(g["tiers"][str(it["tier"])])
                else:
                    prices = []
                prices = (prices + [None, None, None, None])[:4]
                tag = f"tier {it['tier']}" if "tier" in it else ""
                row(ws, r, [f"{g['id']}/{it['name']}", g["name"], it["name"],
                            it.get("desc", ""), *prices,
                            " / ".join(sizes) if sizes else tag], locked=1)
                r += 1

    # ---- Pizza builder ----
    b = menu["builder"]
    ws = sheet(wb, "Pizza builder",
               "What a build-your-own pizza costs. One row per number of toppings, one "
               "column per size. The last row is what each EXTRA topping costs once the "
               "included ones are used up.",
               ["id", "Toppings", *b["sizes"]], [22, 14, 13, 13, 13, 13], locked=1)
    r = 5
    for n, prices in enumerate(b["priceByToppingCount"]):
        row(ws, r, [f"builder.count.{n}", f"{n} topping" + ("s" if n != 1 else ""),
                    *prices], locked=1)
        r += 1
    row(ws, r, ["builder.extra", "Each extra", *b["extraToppingPrice"]], locked=1)
    ws.cell(row=r + 2, column=2, value=(
        "The extra-topping prices were worked out from the steps between the rows above. "
        "Confirm them with the shop before trusting them.")).font = NOTE_FONT

    # ---- Hours ----
    ws = sheet(wb, "Hours",
               "Opening times on a 24-hour clock. Use 25 for 1am the next morning, 26 for "
               "2am. Put \"yes\" in Closed for a day off.",
               ["id", "Day", "Opens", "Closes", "Closed"], [14, 16, 11, 11, 11], locked=2)
    r = 5
    for h in site["hours"]:
        row(ws, r, [f"hours.{h['day']}", h["day"], h.get("open"), h.get("close"),
                    "yes" if h.get("closed") else "no"], locked=2)
        r += 1
    yesno(ws, "E", 5, r - 1)

    # ---- Shop details ----
    ws = sheet(wb, "Shop details",
               "Phone, email, delivery and the ordering links. Tax is a decimal — 0.14 is "
               "14%.", ["id", "What", "Value"], [26, 34, 62], locked=2)
    r = 5
    for key, label, value in (
        ("phone", "Phone number (as shown)", site["phone"]),
        ("phoneLink", "Phone number (for the call button)", site["phoneLink"]),
        ("email", "Email address", site["email"]),
        ("tagline", "Tagline", site["tagline"]),
        ("owner", "Owner line", site["owner"]),
        ("delivery.fee", "Delivery fee", site["delivery"]["fee"]),
        ("delivery.minimum", "Minimum order for delivery", site["delivery"]["minimum"]),
        ("taxRate", "Tax rate (0.14 = 14%)", site["taxRate"]),
        ("ordering.doordash", "DoorDash link", site["ordering"]["doordash"]),
        ("ordering.ubereats", "Uber Eats link", site["ordering"]["ubereats"]),
        ("ordering.skipthedishes", "Skip The Dishes link", site["ordering"]["skipthedishes"]),
        ("seo.description", "Google description (70-165 characters)", site["seo"]["description"]),
    ):
        row(ws, r, [key, label, value], locked=2)
        r += 1

    wb.save(BOOK)
    print(f"wrote {BOOK.name}")
    for ws in wb.worksheets:
        print(f"  {ws.title}")


# --------------------------------------------------------------------- import

class Report:
    def __init__(self):
        self.changes, self.problems = [], []

    @staticmethod
    def same(a, b):
        """15 and 15.0 are the same price. Excel hands back floats, so without
        this a round trip with no edits reports dozens of fake changes and the
        shop stops believing the list."""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(float(a) - float(b)) < 0.005
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(Report.same(x, y) for x, y in zip(a, b))
        return str(a) == str(b)

    def change(self, what, old, new):
        if not self.same(old, new):
            self.changes.append(f"{what}: {old!r} -> {new!r}")

    def problem(self, sheet, cell, msg):
        self.problems.append(f"{sheet}!{cell}  {msg}")


def num(v, rep, ws, cell, what, allow_blank=True):
    if v is None or v == "":
        if allow_blank:
            return None
        rep.problem(ws, cell, f"{what} is empty and needs a number")
        return None
    try:
        n = round(float(v), 2)
        return int(n) if n == int(n) else n
    except (TypeError, ValueError):
        rep.problem(ws, cell, f"{what} should be a number, found {v!r}")
        return None


def text(v):
    return "" if v is None else str(v).strip()


def do_import(dry):
    if not BOOK.exists():
        print(f"no {BOOK.name} — run:  python scripts/control_sheet.py export")
        return 1
    wb = load_workbook(BOOK, data_only=True)
    site, menu, deals = load("site"), load("menu"), load("deals")
    rep = Report()

    # ---- Home page ----
    ws = wb["Home page"]
    home = site["home"]
    wide, phone, facts = [], [], []
    for r in range(5, ws.max_row + 1):
        key, idx, val = ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value
        if not key:
            continue
        val = text(val)
        if key == "home.sloganWide" and val:
            wide.append(val)
        elif key == "home.sloganPhone" and val:
            phone.append(val)
        elif key == "home.eyebrow":
            rep.change("home.eyebrow", home["eyebrow"], val); home["eyebrow"] = val
        elif key == "home.lede":
            rep.change("home.lede", home["lede"], val); home["lede"] = val
        elif key == "home.facts" and val:
            if "|" not in val:
                rep.problem("Home page", f"C{r}", 'a fact needs a | in it, like  Free | parking')
            else:
                a, b = val.split("|", 1)
                facts.append([a.strip(), b.strip()])
    if len(wide) < 2:
        rep.problem("Home page", "C5", "the laptop slogan needs at least two lines")
    if len(phone) < 2:
        rep.problem("Home page", "C7", "the phone slogan needs at least two lines")
    if wide:
        rep.change("home.sloganWide", home["sloganWide"], wide); home["sloganWide"] = wide
    if phone:
        rep.change("home.sloganPhone", home["sloganPhone"], phone); home["sloganPhone"] = phone
    if facts:
        rep.change("home.facts", home["facts"], facts); home["facts"] = facts

    # ---- Deals ----
    ws = wb["Deals"]
    by_id = {d["id"]: d for d in deals["deals"]}
    for r in range(5, ws.max_row + 1):
        did = ws.cell(r, 1).value
        if not did:
            continue
        d = by_id.get(str(did).strip())
        if not d:
            rep.problem("Deals", f"A{r}", f"no deal called {did!r} — was the grey id changed?")
            continue
        on = text(ws.cell(r, 2).value).lower() in ("yes", "y", "true", "1")
        rep.change(f"deal {d['id']}.active", d.get("active"), on); d["active"] = on
        for col, key, label in ((3, "name", "name"), (4, "desc", "description")):
            v = text(ws.cell(r, col).value)
            if key == "name" and not v:
                rep.problem("Deals", f"C{r}", "a deal needs a name")
                continue
            rep.change(f"deal {d['id']}.{key}", d.get(key, ""), v); d[key] = v
        price = num(ws.cell(r, 5).value, rep, "Deals", f"E{r}", "price", allow_blank=False)
        if price is not None:
            rep.change(f"deal {d['id']}.price", d.get("price"), price); d["price"] = price
        was = num(ws.cell(r, 6).value, rep, "Deals", f"F{r}", "was price")
        if was is None:
            d.pop("compareAt", None)
        else:
            if price is not None and was <= price:
                rep.problem("Deals", f"F{r}",
                            f"was price {was} is not above the price {price}, so no saving shows")
            rep.change(f"deal {d['id']}.compareAt", d.get("compareAt"), was); d["compareAt"] = was

    # ---- Menu ----
    ws = wb["Menu"]
    index, tiers = {}, {}
    for c in menu["categories"]:
        for g in c["groups"]:
            for it in g["items"]:
                index[f"{g['id']}/{it['name']}"] = (g, it)
            for tname, prices in (g.get("tiers") or {}).items():
                tiers[(g["id"], tname)] = prices
    seen_tier = {}
    for r in range(5, ws.max_row + 1):
        key = ws.cell(r, 1).value
        if not key:
            continue
        hit = index.get(str(key).strip())
        if not hit:
            rep.problem("Menu", f"A{r}", f"no dish called {key!r} — was the grey id changed?")
            continue
        g, it = hit
        name = text(ws.cell(r, 3).value)
        if not name:
            rep.problem("Menu", f"C{r}", "a dish needs a name")
        elif name != it["name"]:
            rep.change(f"menu {key}.name", it["name"], name); it["name"] = name
        desc = text(ws.cell(r, 4).value)
        rep.change(f"menu {key}.desc", it.get("desc", ""), desc)
        if desc:
            it["desc"] = desc
        else:
            it.pop("desc", None)

        if "prices" in it:
            slots = len(it["prices"])
        elif "tier" in it:
            slots = len(g["tiers"][str(it["tier"])])
        else:
            slots = 1
        vals = [num(ws.cell(r, 5 + i).value, rep, "Menu", f"{get_column_letter(5 + i)}{r}",
                    "price") for i in range(slots)]
        if all(v is None for v in vals):
            continue
        if "tier" in it:
            tkey = (g["id"], str(it["tier"]))
            if tkey in seen_tier and seen_tier[tkey] != vals:
                rep.problem("Menu", f"E{r}",
                            f"tier {it['tier']} was given different prices on two rows; "
                            "every dish on a tier shares one price list")
            seen_tier[tkey] = vals
        elif "prices" in it:
            rep.change(f"menu {key}.prices", it["prices"], vals); it["prices"] = vals
        elif "price" in it and vals[0] is not None:
            rep.change(f"menu {key}.price", it["price"], vals[0]); it["price"] = vals[0]
    for (gid, tname), vals in seen_tier.items():
        for c in menu["categories"]:
            for g in c["groups"]:
                if g["id"] == gid and tname in (g.get("tiers") or {}):
                    rep.change(f"{gid} tier {tname}", g["tiers"][tname], vals)
                    g["tiers"][tname] = vals

    # ---- Pizza builder ----
    ws = wb["Pizza builder"]
    b = menu["builder"]
    for r in range(5, ws.max_row + 1):
        key = text(ws.cell(r, 1).value)
        if not key:
            continue
        vals = [num(ws.cell(r, 3 + i).value, rep, "Pizza builder",
                    f"{get_column_letter(3 + i)}{r}", "price") for i in range(len(b["sizes"]))]
        if any(v is None for v in vals):
            rep.problem("Pizza builder", f"C{r}", "every size needs a price on this row")
            continue
        if key == "builder.extra":
            rep.change("builder.extraToppingPrice", b["extraToppingPrice"], vals)
            b["extraToppingPrice"] = vals
        elif key.startswith("builder.count."):
            n = int(key.rsplit(".", 1)[1])
            if n < len(b["priceByToppingCount"]):
                rep.change(f"builder {n} toppings", b["priceByToppingCount"][n], vals)
                b["priceByToppingCount"][n] = vals

    # ---- Hours ----
    ws = wb["Hours"]
    hours = {h["day"]: h for h in site["hours"]}
    for r in range(5, ws.max_row + 1):
        key = text(ws.cell(r, 1).value)
        if not key.startswith("hours."):
            continue
        h = hours.get(key.split(".", 1)[1])
        if not h:
            rep.problem("Hours", f"A{r}", f"no day called {key!r}")
            continue
        shut = text(ws.cell(r, 5).value).lower() in ("yes", "y", "true", "1")
        rep.change(f"{h['day']} closed", h.get("closed", False), shut)
        if shut:
            h["closed"] = True
        else:
            h.pop("closed", None)
            for col, k in ((3, "open"), (4, "close")):
                v = num(ws.cell(r, col).value, rep, "Hours", f"{get_column_letter(col)}{r}",
                        k, allow_blank=False)
                if v is None:
                    continue
                if not 0 <= v <= 30:
                    rep.problem("Hours", f"{get_column_letter(col)}{r}",
                                f"{v} is not an hour — use 0-24, or 25/26 for 1am/2am")
                    continue
                rep.change(f"{h['day']} {k}", h.get(k), int(v)); h[k] = int(v)

    # ---- Shop details ----
    ws = wb["Shop details"]
    for r in range(5, ws.max_row + 1):
        key = text(ws.cell(r, 1).value)
        if not key:
            continue
        v = ws.cell(r, 3).value
        if key in ("delivery.fee", "delivery.minimum", "taxRate"):
            v = num(v, rep, "Shop details", f"C{r}", key, allow_blank=False)
            if v is None:
                continue
            if key == "taxRate" and not 0 <= v <= 0.5:
                rep.problem("Shop details", f"C{r}",
                            f"tax of {v} looks wrong — 14% is written 0.14")
                continue
        else:
            v = text(v)
            # a delivery app the shop is not on yet is a blank, not a mistake
            if not v and not key.startswith("ordering."):
                rep.problem("Shop details", f"C{r}", f"{key} is empty")
                continue
        target, last = site, key.split(".")
        for part in last[:-1]:
            target = target[part]
        rep.change(key, target.get(last[-1]), v)
        target[last[-1]] = v

    # ---- report ----
    print()
    if rep.problems:
        print(f"{len(rep.problems)} problem(s) — nothing was changed:\n")
        for p in rep.problems:
            print(f"  {p}")
        print("\nFix those in the workbook, save, close it and run this again.")
        return 1
    if not rep.changes:
        print("The workbook matches the website already. Nothing to do.")
        return 0
    print(f"{len(rep.changes)} change(s):\n")
    for c in rep.changes[:40]:
        print(f"  {c}")
    if len(rep.changes) > 40:
        print(f"  ... and {len(rep.changes) - 40} more")
    if dry:
        print("\n(dry run — nothing written)")
        return 0
    save("site", site)
    save("menu", menu)
    save("deals", deals)
    print("\nwritten to data/")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "export"
    if cmd == "export":
        export()
    elif cmd == "import":
        raise SystemExit(do_import("--dry-run" in sys.argv))
    else:
        print(__doc__)
        raise SystemExit(2)

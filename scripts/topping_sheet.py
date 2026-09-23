r"""Render every topping's artwork large, on a cheese background, for review.

The toppings are drawn as SVG in src/app.js. Small on the pizza, they only get
judged properly at size, so this pulls them out and tiles them.

    python scripts/topping_sheet.py     ->  research/_toppings.html
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "src" / "app.js"
OUT = ROOT / "research" / "_toppings.html"

ENTRY = re.compile(
    r"'(?P<name>[^']+)':\s*\{\s*c:\s*'(?P<c>#[0-9A-Fa-f]+)',\s*size:\s*(?P<size>\d+),\s*svg:\s*"
    r"(?P<body>(?:\s*'(?:[^'\\]|\\.)*'\s*\+?)+)\s*\}"
)
PIECE = re.compile(r"'((?:[^'\\]|\\.)*)'")


def main():
    js = JS.read_text(encoding="utf-8")
    start = js.index("var TOPPING_LOOK = {")
    block = js[start:js.index("\n  };", start)]

    cells = []
    for m in ENTRY.finditer(block):
        svg = "".join(PIECE.findall(m.group("body")))
        cells.append(
            '<figure><div class="pad"><svg viewBox="0 0 32 32" '
            'xmlns="http://www.w3.org/2000/svg">' + svg + "</svg></div>"
            '<figcaption><i style="background:' + m.group("c") + '"></i>'
            + m.group("name") + " <b>" + m.group("size") + "</b></figcaption></figure>"
        )

    html = (
        "<!doctype html><meta charset=utf-8><title>toppings</title><style>"
        "body{margin:0;background:#15110F;color:#F6F3EE;font:15px/1.4 system-ui;padding:22px}"
        "h1{font:700 17px system-ui;margin:0 0 16px}"
        ".grid{display:grid;grid-template-columns:repeat(6,1fr);gap:14px}"
        "figure{margin:0;text-align:center}"
        ".pad{background:radial-gradient(circle at 42% 38%,#F7D882,#EDBF55 62%,#DCA637);"
        "border-radius:14px;padding:10px;display:grid;place-items:center}"
        ".pad svg{width:104px;height:104px;filter:drop-shadow(0 2px 2px rgba(96,48,10,.45))}"
        "figcaption{margin-top:6px;font-size:11.5px;display:flex;gap:6px;align-items:center;"
        "justify-content:center}figcaption b{opacity:.45;font-weight:600}"
        "figcaption i{width:11px;height:11px;border-radius:99px;display:inline-block;"
        "box-shadow:inset 0 0 0 1px rgba(0,0,0,.25)}"
        "</style><h1>Topping artwork, shown on cheese</h1><div class=grid>"
        + "".join(cells) + "</div>"
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"{len(cells)} toppings -> {OUT}")


if __name__ == "__main__":
    main()

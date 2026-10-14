#!/usr/bin/env python3
"""Build self-contained voucher pages from base/template.html.

Each voucher lives in vouchery/<name>/ with:
  voucher.json  title, slug, and one of: "dates" {start, end, year}, "flex": true
                (~ 4 dni, termín podľa dohody), "amounts": [50, 100] (one page per
                value, slug-<amount>), or "stub" (raw SVG)
                optional: "titleSize" (default 104), "aria" (overrides the generated label)
  scene.svg     the left-panel illustration (snowflakes, star, landscape); drawn
                under the title, so keep x < 480, y < 240 clear

Output: poukaz-<slug>.html in the project root, and docs/<slug>.png (2590×996,
rendered with headless Chrome) for GitHub Pages.

Usage: python3 build.py            # all vouchers
       python3 build.py dolomity   # just one
"""
import json
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
TEMPLATE = (ROOT / "base" / "template.html").read_text(encoding="utf-8")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Pin the SVG to the 1295×498 viewport so the screenshot is exactly the voucher.
PNG_CSS = "<style>body { padding: 0; } svg { width: 1295px; max-width: none; }</style></head>"


def render_png(html: str, out: Path):
    out.parent.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as f:
        f.write(html.replace("</head>", PNG_CSS, 1))
    cmd = [
        CHROME, "--headless=new", "--hide-scrollbars",
        "--window-size=1295,498", "--force-device-scale-factor=2",
        "--virtual-time-budget=10000",  # give Google Fonts time to load
        f"--screenshot={out}", Path(f.name).as_uri(),
    ]
    # Headless Chrome occasionally hangs instead of exiting; retry once.
    for attempt in range(2):
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            break
        except subprocess.TimeoutExpired:
            if attempt:
                raise
    Path(f.name).unlink()


def date_stub(d):
    return "\n".join([
        '    <text x="1010" y="130" class="sans" font-size="19" opacity="0.7">Termín</text>',
        f'    <text x="1010" y="202" class="serif" font-size="56">{escape(d["start"])}</text>',
        '    <text x="1010" y="242" class="sans" font-size="18" opacity="0.7">až</text>',
        f'    <text x="1010" y="302" class="serif" font-size="56">{escape(d["end"])}</text>',
        f'    <text x="1010" y="346" class="sans" font-size="22" letter-spacing="6">{escape(d["year"])}</text>',
    ])


# Stub for vouchers without fixed dates: about 4 days, picked by agreement.
FLEX_STUB = "\n".join([
    '    <text x="1010" y="130" class="sans" font-size="19" opacity="0.7">Termín</text>',
    '    <text x="1010" y="202" class="serif" font-size="56">~ 4 dni</text>',
    '    <text x="1010" y="242" class="sans" font-size="18" opacity="0.7">predĺžený víkend</text>',
    '    <text x="1010" y="302" class="serif" font-size="40">podľa</text>',
    '    <text x="1010" y="346" class="serif" font-size="40">dohody</text>',
])


def amount_stub(amount):
    return "\n".join([
        '    <text x="1010" y="176" class="sans" font-size="19" opacity="0.7">Hodnota</text>',
        f'    <text x="1010" y="256" class="serif" font-size="76">{amount} €</text>',
    ])


def variants(cfg):
    """(slug, stub, aria) for each page a voucher produces."""
    title, slug = cfg["title"], cfg["slug"]
    if "amounts" in cfg:
        return [(f"{slug}-{a}", amount_stub(a), f"Darčekový poukaz: {title}, hodnota {a} €")
                for a in cfg["amounts"]]
    if "dates" in cfg:
        d = cfg["dates"]
        stub = date_stub(d)
        aria = f'Darčekový poukaz: {title}, {d["start"]} až {d["end"]} {d["year"]}'
    elif cfg.get("flex"):
        stub = FLEX_STUB
        aria = f"Darčekový poukaz: {title}, približne 4 dni, predĺžený víkend, termín podľa dohody"
    else:
        stub = cfg["stub"].rstrip("\n")
        aria = f"Darčekový poukaz: {title}"
    return [(slug, stub, cfg.get("aria", aria))]


def build(folder: Path):
    cfg = json.loads((folder / "voucher.json").read_text(encoding="utf-8"))
    title = cfg["title"]
    scene = (folder / "scene.svg").read_text(encoding="utf-8").rstrip("\n")

    for slug, stub, aria in variants(cfg):
        html = (TEMPLATE
                .replace("{{TITLE}}", escape(title))
                .replace("{{TITLE_SIZE}}", str(cfg.get("titleSize", 104)))
                .replace("{{ARIA}}", escape(aria))
                .replace("{{SCENE}}", scene)
                .replace("{{STUB}}", stub))

        out = ROOT / f"poukaz-{slug}.html"
        out.write_text(html, encoding="utf-8")
        png = ROOT / "docs" / f"{slug}.png"
        render_png(html, png)
        print(f"built {out.name}, docs/{png.name}")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.name for p in (ROOT / "vouchery").iterdir() if p.is_dir())
    for name in names:
        build(ROOT / "vouchery" / name)

#!/usr/bin/env python3
"""Build self-contained voucher pages from base/template.html.

Each voucher lives in vouchery/<name>/ with:
  voucher.json  title, slug, and either "dates" {start, end, year} or "stub" (raw SVG)
                optional: "titleSize" (default 104), "aria" (overrides the generated label)
  scene.svg     the left-panel illustration (snowflakes, star, landscape); drawn
                under the title, so keep x < 480, y < 240 clear

Output: poukaz-<slug>.html in the project root, and docs/<slug>.png (2400×1200,
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
# Pin the SVG to the 1200×600 viewport so the screenshot is exactly the voucher.
PNG_CSS = "<style>body { padding: 0; } svg { width: 1200px; max-width: none; }</style></head>"


def render_png(html: str, out: Path):
    out.parent.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as f:
        f.write(html.replace("</head>", PNG_CSS, 1))
    subprocess.run([
        CHROME, "--headless=new", "--hide-scrollbars",
        "--window-size=1200,600", "--force-device-scale-factor=2",
        "--virtual-time-budget=10000",  # give Google Fonts time to load
        f"--screenshot={out}", Path(f.name).as_uri(),
    ], check=True, capture_output=True)
    Path(f.name).unlink()


def date_stub(d):
    return "\n".join([
        '    <text x="1010" y="130" class="sans" font-size="19" opacity="0.7">Termín</text>',
        f'    <text x="1010" y="202" class="serif" font-size="56">{escape(d["start"])}</text>',
        '    <text x="1010" y="242" class="sans" font-size="18" opacity="0.7">až</text>',
        f'    <text x="1010" y="302" class="serif" font-size="56">{escape(d["end"])}</text>',
        f'    <text x="1010" y="346" class="sans" font-size="22" letter-spacing="6">{escape(d["year"])}</text>',
    ])


def build(folder: Path):
    cfg = json.loads((folder / "voucher.json").read_text(encoding="utf-8"))
    title = cfg["title"]
    scene = (folder / "scene.svg").read_text(encoding="utf-8").rstrip("\n")

    if "dates" in cfg:
        d = cfg["dates"]
        stub = date_stub(d)
        aria = f'Darčekový poukaz: {title}, {d["start"]} až {d["end"]} {d["year"]}'
    else:
        stub = cfg["stub"].rstrip("\n")
        aria = f"Darčekový poukaz: {title}"
    aria = cfg.get("aria", aria)

    html = (TEMPLATE
            .replace("{{TITLE}}", escape(title))
            .replace("{{TITLE_SIZE}}", str(cfg.get("titleSize", 104)))
            .replace("{{ARIA}}", escape(aria))
            .replace("{{SCENE}}", scene)
            .replace("{{STUB}}", stub))

    out = ROOT / f'poukaz-{cfg["slug"]}.html'
    out.write_text(html, encoding="utf-8")
    png = ROOT / "docs" / f'{cfg["slug"]}.png'
    render_png(html, png)
    print(f"built {out.name}, docs/{png.name}")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.name for p in (ROOT / "vouchery").iterdir() if p.is_dir())
    for name in names:
        build(ROOT / "vouchery" / name)

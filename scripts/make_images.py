#!/usr/bin/env python3
"""Regenerate the optimized image assets from their sources.

    python scripts/make_images.py

Writes (into assets/img/):
  profile-320.webp  320x320 WebP of profile.jpg, used in the sidebar (displayed at 160px, 2x for retina)
  social-card.png   1200x630 link-preview image used for Open Graph / Twitter cards

Needs Pillow, and Playwright + Chromium (the same ones `build.py --pdf` uses).
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"


def make_profile() -> Path:
    out = IMG / "profile-320.webp"
    with Image.open(IMG / "profile.jpg") as im:
        im.convert("RGBA").resize((320, 320), Image.LANCZOS).save(out, "WEBP", quality=82, method=6)
    return out


def make_social_card(data: dict) -> Path:
    from playwright.sync_api import sync_playwright

    person, stats = data["person"], data["stats"][:3]
    chips = "".join(
        f'<div class="chip"><b>{html.escape(s["value"])}</b><span>{html.escape(s["label"])}</span></div>' for s in stats
    )
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:PJS;font-weight:400;src:url(../fonts/plus-jakarta-sans-latin-400-normal.woff2)}}
@font-face{{font-family:PJS;font-weight:800;src:url(../fonts/plus-jakarta-sans-latin-800-normal.woff2)}}
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;display:flex;font-family:PJS,Arial,sans-serif;background:#f7f3ea;color:#1d261c}}
.side{{flex:none;width:380px;background:#2c4a2c;display:flex;align-items:center;justify-content:center}}
.side img{{width:260px;height:260px;border-radius:58% 42% 55% 45% / 48% 54% 46% 52%;object-fit:cover;border:8px solid #f7f3ea;background:#fff}}
.main{{flex:1;padding:70px 70px 60px;display:flex;flex-direction:column;justify-content:center}}
h1{{font-weight:800;font-size:92px;line-height:1.02;letter-spacing:-2px}}
h1 em{{font-style:normal;color:#355a35;display:block}}
.title{{font-size:34px;font-weight:800;margin:26px 0 8px}}
.sub{{font-size:26px;color:#5a574d}}
.chips{{display:flex;gap:16px;margin-top:38px}}
.chip{{background:#fcfaf4;border:2px solid #cfc7b3;border-radius:14px;padding:14px 20px;display:flex;flex-direction:column;gap:4px}}
.chip b{{font-weight:800;font-size:42px;line-height:1;color:#355a35}}
.chip span{{font-size:18px;color:#5a574d;max-width:190px;line-height:1.25}}
</style></head><body>
<div class="side"><img src="profile.jpg" alt=""></div>
<div class="main">
<h1>{html.escape(person['first'])}<em>{html.escape(person['last'])}</em></h1>
<div class="title">{html.escape(person['job_title'])}</div>
<div class="sub">{html.escape(person['location'])}</div>
<div class="chips">{chips}</div>
</div></body></html>"""
    tmp = IMG / ".social-card.tmp.html"
    tmp.write_text(page, encoding="utf-8")
    out = IMG / "social-card.png"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                pg = browser.new_page(viewport={"width": 1200, "height": 630})
                pg.goto(tmp.as_uri())
                pg.evaluate("document.fonts.ready")
                pg.screenshot(path=str(out))
            finally:
                browser.close()
    finally:
        tmp.unlink(missing_ok=True)
    return out


def main() -> int:
    data = json.loads((ROOT / "data" / "resume.json").read_text(encoding="utf-8"))
    for path in (make_profile(), make_social_card(data)):
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

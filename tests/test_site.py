"""Safety net for the resume site: run with `pytest -q`."""
from __future__ import annotations

import hashlib
import base64
import json
import re
import struct
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import pytest

import build

HTML_PAGES = ("index.html", "404.html")
# Anchored so DOIs and other digit runs inside identifiers do not match
PHONE_RE = re.compile(r"(?<![\w/])(?:\+?\d{1,3}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\w)")


class Page(HTMLParser):
    """Collects ids, links, resource URLs and inline scripts."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.urls: list[tuple[str, str]] = []  # (tag, url)
        self.inline_scripts: list[str] = []
        self.jsonld: list[str] = []
        self._script: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if a.get(key):
                self.urls.append((tag, a[key]))
        if tag == "script" and not a.get("src"):
            self._script = {"type": a.get("type", ""), "text": ""}

    def handle_data(self, data):
        if self._script is not None:
            self._script["text"] += data

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            (self.jsonld if self._script["type"] == "application/ld+json" else self.inline_scripts).append(self._script["text"])
            self._script = None


def parse(html: str) -> Page:
    page = Page()
    page.feed(html)
    return page


# ---------------------------------------------------------------- data and build
def test_data_validates(data):
    build.validate(data)


def test_committed_output_is_up_to_date(env, data):
    stale = build.stale_files(env, data)
    assert not stale, f"run `python build.py`; out of date: {[p.name for p in stale]}"


def test_build_is_deterministic(env, data):
    first = build.render_pages(env, data)
    second = build.render_pages(env, data)
    assert first == second


def test_validation_rejects_unknown_focus_role(data):
    broken = json.loads(json.dumps(data))
    broken["focus_areas"][0]["roles"] = ["does-not-exist"]
    with pytest.raises(build.BuildError):
        build.validate(broken)


def test_validation_requires_updated_date(data):
    broken = json.loads(json.dumps(data))
    broken["site"]["updated"] = "yesterday"
    with pytest.raises(build.BuildError):
        build.validate(broken)


# ---------------------------------------------------------------- privacy
def test_no_phone_number_in_public_pages(root, pages, data):
    texts = {name: pages[name] for name in HTML_PAGES}
    texts["resume.json"] = (root / "data" / "resume.json").read_text(encoding="utf-8")
    texts["README.md"] = (root / "README.md").read_text(encoding="utf-8")
    for name, text in texts.items():
        assert "tel:" not in text, f"tel: link in {name}"
        assert not PHONE_RE.search(text), f"phone-like number in {name}"
    private = root / "data" / "private.json"
    if private.exists():
        digits = re.sub(r"\D", "", json.loads(private.read_text(encoding="utf-8")).get("phone", ""))
        if len(digits) >= 7:
            for name, text in texts.items():
                assert digits[-7:] not in re.sub(r"\D", "", text), f"private phone digits found in {name}"


def test_private_file_is_gitignored(root):
    lines = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "data/private.json" in [l.strip() for l in lines]


# ---------------------------------------------------------------- links and resources
@pytest.mark.parametrize("name", HTML_PAGES)
def test_internal_links_and_resources_exist(root, pages, name):
    page = parse(pages[name])
    for tag, url in page.urls:
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https", "mailto", "data"):
            continue
        if url.startswith("#"):
            assert url[1:] in page.ids, f"{name}: dangling anchor {url}"
            continue
        target = root / parsed.path.lstrip("/")
        assert target.exists(), f"{name}: <{tag}> points to missing file {url}"


@pytest.mark.parametrize("name", HTML_PAGES)
def test_external_links_use_https(pages, name):
    for tag, url in parse(pages[name]).urls:
        scheme = urlparse(url).scheme
        assert scheme in ("", "https", "mailto", "data"), f"{name}: insecure link {url}"


def test_fonts_referenced_by_css_exist(root):
    css = (root / "css" / "custom.css").read_text(encoding="utf-8")
    fonts = re.findall(r'url\("\.\./([^"]+\.woff2)"\)', css)
    assert fonts, "no @font-face sources found"
    for rel in fonts:
        assert (root / rel).exists(), f"missing font {rel}"


def test_pdf_is_present_and_small(root, data):
    pdf = root / data["site"]["pdf_path"]
    assert pdf.exists()
    head = pdf.read_bytes()[:5]
    assert head == b"%PDF-"
    assert pdf.stat().st_size < 300_000


def test_share_and_structured_data_images_exist(root, pages, data):
    html = pages["index.html"]
    og = re.search(r'property="og:image" content="([^"]+)"', html).group(1)
    ld = json.loads(parse(html).jsonld[0])["image"]
    prefix = data["site"]["url"]
    for url in (og, ld):
        assert url.startswith(prefix), url
        assert (root / url[len(prefix):]).exists(), f"missing image {url}"


def test_social_card_dimensions(root):
    with open(root / "assets" / "img" / "social-card.png", "rb") as fh:
        header = fh.read(24)
    width, height = struct.unpack(">II", header[16:24])
    assert (width, height) == (1200, 630)


# ---------------------------------------------------------------- markup quality
def test_json_ld_is_valid(pages, data):
    page = parse(pages["index.html"])
    assert len(page.jsonld) == 1
    doc = json.loads(page.jsonld[0])
    assert doc["@type"] == "Person"
    assert doc["name"] == data["person"]["name"]
    assert doc["url"] == data["site"]["url"]


@pytest.mark.parametrize("name", HTML_PAGES)
def test_csp_allows_only_the_known_inline_script(pages, name):
    html = pages[name]
    page = parse(html)
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)
    assert csp, "missing CSP"
    policy = csp.group(1).replace("&#39;", "'")
    assert "unsafe-inline" not in policy and "unsafe-eval" not in policy
    assert len(page.inline_scripts) == 1
    digest = base64.b64encode(hashlib.sha256(page.inline_scripts[0].encode("utf-8")).digest()).decode("ascii")
    assert f"'sha256-{digest}'" in policy


def test_no_inline_svg_metadata(pages):
    assert "<metadata" not in pages["index.html"]
    assert "c2pa" not in pages["index.html"]


def test_page_weight_budget(root, pages):
    assert len(pages["index.html"].encode("utf-8")) < 60_000
    css_bytes = sum((root / "css" / f).stat().st_size for f in ("custom.css",))
    assert css_bytes < 60_000


def test_sitemap_matches_data(pages, data):
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.fromstring(pages["sitemap.xml"])
    assert root.find("s:url/s:loc", ns).text == data["site"]["url"]
    assert root.find("s:url/s:lastmod", ns).text == data["site"]["updated"]


def test_every_page_has_title_description_and_lang(pages):
    for name in HTML_PAGES:
        html = pages[name]
        assert '<html lang="en">' in html
        assert re.search(r"<title>[^<]+</title>", html)
        assert 'name="description"' in html


# ---------------------------------------------------------------- design tokens
def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ratio(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _blend(fg: str, bg: str, alpha: float) -> str:
    f = [int(fg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(round(alpha * x + (1 - alpha) * y) for x, y in zip(f, b))


def _tokens(css: str, selector: str) -> dict[str, str]:
    block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert block, f"token block {selector} not found"
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;", block.group(1)))


@pytest.mark.parametrize("theme,selector", [("light", ":root"), ("dark", ':root[data-theme="dark"]')])
def test_palette_meets_wcag_aa(root, theme, selector):
    css = (root / "css" / "custom.css").read_text(encoding="utf-8")
    t = _tokens(css, selector)
    pairs = [
        ("text", "bg"), ("text", "bg-alt"), ("muted", "bg"), ("muted", "bg-alt"),
        ("heading", "bg"), ("heading", "bg-alt"), ("accent", "bg"), ("accent", "bg-alt"),
        ("on-accent", "accent"), ("btn-fg", "btn-bg"), ("btn-hover-fg", "btn-hover-bg"),
    ]
    for fg, bg in pairs:
        assert _ratio(t[fg], t[bg]) >= 4.5, f"{theme}: {fg} on {bg} = {_ratio(t[fg], t[bg]):.2f}"
    # The footer band uses white text on the band colour
    assert _ratio("#ffffff", t["band"]) >= 4.5, f"{theme}: white on band"
    assert _ratio(t["band"], "#ffffff") >= 4.5, f"{theme}: band on white (primary footer button)"
    # Tag text sits on a tinted background
    tint = {"light": 0.09, "dark": 0.12}[theme]
    assert _ratio(t["accent"], _blend(t["accent"], t["bg-alt"], tint)) >= 4.5, f"{theme}: tag text"

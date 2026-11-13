#!/usr/bin/env python3
"""
Build the resume site (and optionally the PDF) from data/resume.json.

Usage:
    python build.py            # index.html, 404.html, sitemap.xml
    python build.py --pdf      # also render assets/<resume>.pdf (needs Playwright + Chromium)

The phone number is deliberately NOT in resume.json. Put it in data/private.json
(git-ignored) and it is added to the PDF only, never to the website.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "resume.json"
PRIVATE_FILE = ROOT / "data" / "private.json"
TEMPLATES = ROOT / "templates"

log = logging.getLogger("build")

REQUIRED_KEYS = (
    "site",
    "person",
    "status",
    "summary_short",
    "summary_full",
    "nav",
    "stats",
    "focus_areas",
    "experience",
    "earlier",
    "projects",
    "publications",
    "skills",
    "languages",
    "education",
    "certifications",
)


class BuildError(Exception):
    """Raised for problems the user should fix in the data or environment."""


# --------------------------------------------------------------------------- data
def load_json(path: Path, *, required: bool) -> dict:
    if not path.exists():
        if required:
            raise BuildError(f"Missing data file: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BuildError(f"{path.name} is not valid JSON: {exc}") from exc


def validate(data: dict) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise BuildError(f"resume.json is missing keys: {', '.join(missing)}")

    role_ids = [r.get("id") for r in data["experience"]]
    if len(role_ids) != len(set(role_ids)) or None in role_ids:
        raise BuildError("Every experience entry needs a unique 'id'.")

    for focus in data["focus_areas"]:
        unknown = [r for r in focus.get("roles", []) if r not in role_ids]
        if unknown:
            raise BuildError(
                f"focus area '{focus.get('title')}' references unknown role ids: {unknown}"
            )

    nav_ids = {n["id"] for n in data["nav"]}
    expected = {"about", "experience", "projects", "skills", "education"}
    if not nav_ids <= expected:
        raise BuildError(
            f"nav ids must be among {sorted(expected)}; got {sorted(nav_ids)}"
        )

    for project in data["projects"]:
        if not str(project.get("url", "")).startswith("https://"):
            raise BuildError(f"project '{project.get('name')}' needs an https:// url")


# --------------------------------------------------------------------------- rendering
_SVG_METADATA = re.compile(
    r"<metadata>.*?</metadata>|\sxmlns:c2pa=\"[^\"]*\"", re.DOTALL
)


def clean_svg(text: str) -> str:
    """
    Drop <metadata> blocks (e.g. embedded C2PA provenance manifests that some tools add
    to image files). Icons are inlined into every page, so this keeps the HTML lean.
    """
    return _SVG_METADATA.sub("", text).strip()


def make_env() -> Environment:
    """
    Create and configure a Jinja2 environment for rendering templates.
    """
    icons = {
        p.stem: Markup(clean_svg(p.read_text(encoding="utf-8")))
        for p in (TEMPLATES / "icons").glob("*.svg")
    }

    def icon(name: str) -> Markup:
        try:
            return icons[name]
        except KeyError:
            raise BuildError(
                f"Unknown icon '{name}' (available: {sorted(icons)})"
            ) from None

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "j2"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["icon"] = icon
    return env


def json_ld(data: dict) -> str:
    """
    Generate a JSON-LD representation of the person and site data.
    """
    person, site = data["person"], data["site"]
    loc = person["location_parts"]
    doc: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": person["name"],
        "jobTitle": person["job_title"],
        "url": site["url"],
        "image": f"{site['url']}assets/img/profile.png",
        "sameAs": [person["linkedin"], person["github"]],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": loc["city"],
            "addressRegion": loc["region"],
            "addressCountry": loc["country"],
        },
        "alumniOf": [
            {"@type": "CollegeOrUniversity", "name": "Arizona State University"},
            {
                "@type": "CollegeOrUniversity",
                "name": "Birla Institute of Technology and Science, Pilani",
            },
        ],
        "knowsAbout": [
            "Machine Learning",
            "Computer Vision",
            "Generative AI",
            "Retrieval-Augmented Generation",
            "Agentic AI",
            "Natural Language Processing",
            "Microsoft Azure",
            "Python",
        ],
    }
    # "</" inside a <script> block would end it early; escape defensively.
    return json.dumps(doc, indent=2, ensure_ascii=False).replace("</", "<\\/")


def context(data: dict, *, root: str) -> dict[str, Any]:
    """
    Build the context dictionary for rendering templates.
    """
    roles_by_id = {r["id"]: r for r in data["experience"]}
    focus = [
        {
            **f,
            "role_refs": [
                {"id": rid, "org": roles_by_id[rid]["org"]} for rid in f["roles"]
            ],
        }
        for f in data["focus_areas"]
    ]
    years = [int(e["start"][-4:]) for e in data["earlier"]] + [
        int(e["end"][-4:]) for e in data["earlier"]
    ]
    ctx = {
        **data,
        "focus_areas": focus,
        "root": root,
        "year": dt.date.today().year,
        "earlier_span": f"{min(years)} – {max(years)}",
        "jsonld": json_ld(data),
    }
    return ctx


def write(path: Path, text: str) -> None:
    """
    Write the given text to the specified path, creating parent directories if needed.
    Logs the action.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    log.info("wrote %s (%d bytes)", path.relative_to(ROOT), path.stat().st_size)


def build_site(env: Environment, data: dict) -> None:
    """
    Build the static site by rendering templates and writing output files.

    Args:
        env (Environment): The Jinja2 environment for rendering templates.
        data (dict): The site data used for rendering templates.
    """
    write(
        ROOT / "index.html",
        env.get_template("index.html.j2").render(context(data, root="")),
    )
    write(
        ROOT / "404.html",
        env.get_template("404.html.j2").render(context(data, root="/")),
    )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url>\n    <loc>{data['site']['url']}</loc>\n"
        f"    <lastmod>{dt.date.today().isoformat()}</lastmod>\n  </url>\n</urlset>\n"
    )
    write(ROOT / "sitemap.xml", sitemap)


def build_pdf(env: Environment, data: dict, private: dict) -> None:
    """
    Build the PDF version of the resume using Playwright.

    Args:
        env (Environment): The Jinja2 environment for rendering templates.
        data (dict): The site data used for rendering templates.
        private (dict): Private data, such as phone number, used in the PDF.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BuildError(
            "PDF build needs Playwright: pip install playwright && playwright install chromium"
        ) from exc

    phone = private.get("phone", "")
    if not phone:
        log.warning(
            "data/private.json has no 'phone'; the PDF will be built without one."
        )
    html = env.get_template("resume_pdf.html.j2").render(
        context(data, root="") | {"phone": phone}
    )

    out = ROOT / data["site"]["pdf_path"]
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_html = ROOT / "data" / ".resume_pdf.tmp.html"  # git-ignored scratch file
    tmp_html.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(tmp_html.as_uri())
                page.pdf(
                    path=str(out), prefer_css_page_size=True, print_background=True
                )
            finally:
                browser.close()
    except Exception as exc:  # Playwright raises its own Error types
        raise BuildError(f"PDF rendering failed: {exc}") from exc
    finally:
        tmp_html.unlink(missing_ok=True)
    log.info("wrote %s (%d bytes)", out.relative_to(ROOT), out.stat().st_size)


# --------------------------------------------------------------------------- cli
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--pdf", action="store_true", help="also render the PDF resume")
    parser.add_argument("--pdf-only", action="store_true", help="render only the PDF")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        data = load_json(DATA_FILE, required=True)
        validate(data)
        private = load_json(PRIVATE_FILE, required=False)
        env = make_env()
        if not args.pdf_only:
            build_site(env, data)
        if args.pdf or args.pdf_only:
            build_pdf(env, data, private)
    except BuildError as exc:
        log.error("ERROR: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

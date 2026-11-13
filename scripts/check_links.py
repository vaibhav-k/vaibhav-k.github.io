#!/usr/bin/env python3
"""
Check that every external link on the site still resolves (stdlib only).

    python scripts/check_links.py

Sites that block bots (LinkedIn answers 999, others 403/429) are reported as
"skipped" rather than failures.
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
BOT_BLOCKED = {401, 403, 405, 429, 999}
# Hosts that refuse or drop automated requests; listed instead of failing the run
SKIP_HOSTS = {"www.linkedin.com", "linkedin.com"}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; resume-link-check/1.0)"}


class Links(HTMLParser):
    """HTML parser that collects all external links starting with 'https://'."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: set[str] = set()

    def handle_starttag(self, tag, attrs):
        href: str | None = dict(attrs).get("href", "")
        if href and href.startswith("https://"):
            self.urls.add(href)


def status_of(url: str) -> int:
    """Return the HTTP status code of the given URL, trying HEAD first and then GET if necessary."""
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers=HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405, 501):
                continue  # some servers reject HEAD; retry with GET
            return exc.code
        except OSError:
            return 0
    return 0


def is_ok(code: int) -> bool:
    """True for a real HTTP response below 400 (0 means no response at all)."""
    return 0 < code < 400


def fetch_with_retries(url: str, attempts: int = 3) -> int:
    """Return the first successful status code, or the last one seen after all retries."""
    code = 0
    for attempt in range(attempts):
        code = status_of(url)
        if is_ok(code):
            break
        if attempt < attempts - 1:
            time.sleep(2 * (attempt + 1))
    return code


def check_link(url: str) -> bool:
    """Check one link and print the result. Returns True only if it counts as a failure."""
    if urlparse(url).hostname in SKIP_HOSTS:
        print(f"skipped  --  {url} (host blocks automated checks)")
        return False

    code = fetch_with_retries(url)
    if is_ok(code):
        print(f"ok       {code} {url}")
        return False
    if code in BOT_BLOCKED:
        print(f"skipped  {code} {url} (site blocks automated checks)")
        return False

    print(f"FAILED   {code or 'no response'} {url}")
    return True


def collect_links() -> set[str]:
    """All external https links found in the generated index.html."""
    parser = Links()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    return parser.urls


def main() -> int:
    urls = collect_links()
    failures = sum(check_link(url) for url in sorted(urls))
    print(f"{len(urls)} links checked, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

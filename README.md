# vaibhav-k.github.io

Personal resume site, generated from a single data file and served by GitHub Pages.

## Edit content
Everything on the site and in the PDF comes from `data/resume.json`.
Edit it, bump `site.updated` to today's date, then:

```
pip install -r requirements.txt
python build.py            # regenerates index.html, 404.html, sitemap.xml
python build.py --check    # verifies the committed output matches data + templates (CI runs this)
```

Never edit `index.html`, `404.html` or `sitemap.xml` by hand: the next build overwrites them.

## PDF and images
```
pip install -r requirements-media.txt && playwright install chromium   # first time only
python build.py --pdf            # also regenerates assets/Vaibhav_Kulshrestha_Resume.pdf
python scripts/make_images.py    # profile-320.webp and the 1200x630 social-card.png
```

The phone number is never on the website. Copy `data/private.example.json` to `data/private.json`
(git-ignored) and set `phone`; it is added to the PDF only. A test fails if a phone-like number
appears in any public page.

## Tests and CI
```
pip install -r requirements-dev.txt
pytest -q
```
Checks: data validation, output up to date and deterministic, no phone number or click-to-call links,
internal links/anchors/files exist, external links use https, JSON-LD valid, CSP matches the one inline
script, sitemap, size budgets, and WCAG AA contrast for both colour themes.

- `.github/workflows/ci.yml` runs `build.py --check` and `pytest` on every push and pull request.
- `.github/workflows/links.yml` checks external links every Monday (`python scripts/check_links.py`).
- Dependabot updates the GitHub Actions and pip dependencies monthly.

## Layout
- `templates/` Jinja templates (`index.html.j2`, `404.html.j2`, `resume_pdf.html.j2`, `icons/`)
- `css/custom.css` hand-written styles (light/dark tokens, layout) and the `@font-face` rules
- `css/print.css` print stylesheet (loaded with `media="print"`): no nav or buttons, compact two-page resume
- `js/scripts.js` nav, scroll spy, theme toggle, scroll reveal, print helper (no libraries)
- `assets/fonts/` self-hosted Plus Jakarta Sans (SIL Open Font License)
- `scripts/` image generation and the external link checker

The site loads nothing from third parties and ships a strict Content-Security-Policy
(a `<meta>` tag whose script hash is computed by `build.py`).

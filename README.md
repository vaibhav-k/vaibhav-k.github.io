# vaibhav-k.github.io

Personal resume site, generated from a single data file.

## Edit content
Everything on the site and in the PDF comes from `data/resume.json`. Edit it, then:

```
pip install -r requirements.txt
python build.py            # regenerates index.html, 404.html, sitemap.xml
python build.py --pdf      # also regenerates assets/Vaibhav_Kulshrestha_Resume.pdf
```

First time only for the PDF: `playwright install chromium`.

## Phone number
The phone number is never on the website. Copy `data/private.example.json` to `data/private.json`
(git-ignored) and set `phone`; it is added to the PDF only.

## Layout
- `templates/` Jinja templates (`index.html.j2`, `404.html.j2`, `resume_pdf.html.j2`, `icons/`)
- `css/custom.css` hand-written styles (light/dark, timeline, print)
- `css/styles.css` Bootstrap theme, purged to the classes the templates use
- `src/styles.full.css` the full theme; re-purge with `npx purgecss --config purgecss.config.cjs` after adding new Bootstrap classes to a template
- `js/scripts.js` scrollspy, nav collapse, scroll reveal, print helper

# Nii Yartey Gidiglo - Portfolio

Personal portfolio site for a Cloud Infrastructure / DevOps / Data Engineer, built as plain
HTML, CSS and JavaScript and served on Azure App Service (Linux, Python) by a small Flask
static-file server.

Live site: https://portfoliosite-fuedesckb9cxe3cf.uksouth-01.azurewebsites.net

## Pages

| Page | Content |
| --- | --- |
| `index.html` | Hero, headline numbers, and the four practice areas (cloud architecture, DevOps/IaC, security, data & AI) |
| `education.html` | Degrees plus community work, recognition and technical writing |
| `experience.html` | Roles grouped into collapsible sections: cloud engineering, data & AI, earlier roles |
| `projects.html` | Twelve delivery engagements with scope and outcome, ten GitHub repositories, plus writing links |
| `certifications.html` | Microsoft, AWS, Oracle, CNCF and ISO credentials, rendered from the JSON store |
| `admin.html` | Password-protected editor for every section of the site |
| `contact.html` | Email, phone, location, social links and areas of work |

## Design

- Palette: deep indigo ground with aurora teal (`#19e3c0`), violet (`#9a7bff`) and a warm amber
  highlight. Both themes are defined as custom properties at the top of `style.css`.
- The background runs three layers: a drifting aurora gradient, an illustrated scene of contours
  and constellations, and a 3D motion canvas - a rotating torus-knot ribbon with an orbiting
  particle shell, projected with perspective so depth drives size, brightness and draw order.
  Glass cards (`backdrop-filter`) sit on top of it.
- Light and dark themes. The first visit follows the operating system preference; the toggle in
  the navigation bar overrides it and the choice is stored in `localStorage`.
- Gradient headings, a scroll progress bar, floating illustrations and hover lift on every card.
- Responsive down to 375px, with a collapsing navigation menu below 900px.
- Illustrations are hand-written SVG in `assets/img/` - no external asset or font requests, so
  the site loads with no third-party dependencies.
- Scroll-reveal animations respect `prefers-reduced-motion`.

## Editing the site

Every section is stored as JSON on the web app's persistent volume and rendered from
`/api/content`. Sign in at `/admin` to edit any of it - no code changes, no redeploy:

| Page | Editable sections |
| --- | --- |
| Home | Intro (name, tagline, introduction), headline numbers, what I do |
| Education | Degrees, beyond the classroom |
| Experience | Roles, grouped into the collapsible sections |
| Projects | Selected work, GitHub repositories, writing |
| Certifications | Certifications (with certificate upload), community and recognition |
| Contact | Contact details, what I can help with |

Each section supports add, edit, delete and reorder; certifications also take a file upload
(PNG, JPG, WEBP, GIF or PDF up to 8 MB). The admin forms are generated from
[content_schema.py](content_schema.py) - add a field there and it appears in the editor.

The admin area is disabled until `ADMIN_PASSWORD` is set on the web app, and every write
endpoint requires that session. See [DEPLOY.md](DEPLOY.md#turning-on-the-site-admin).

If the API is unreachable, each page falls back to the markup shipped in its HTML, so nothing
ever renders empty.

## Running locally

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python app.py
```

The site is then at http://localhost:8000. Set `PORT` to use a different port.

Because the site is fully static, `python -m http.server` also works for a quick look - the
Flask app exists to give App Service a WSGI entry point, add a `/healthz` probe, set cache
headers and serve extensionless URLs such as `/projects`.

## Deployment

Pushes to `main` deploy to the `portfoliosite` web app through
[.github/workflows/main_portfoliosite.yml](.github/workflows/main_portfoliosite.yml), the
workflow the Azure portal's Deployment Center generated when the web app was connected to this
repository. It signs in with federated credentials, so no publish profile or password is stored.

`deploy-azure.sh` provisions the App Service plan and web app from scratch and can also deploy
directly with `az webapp up`, which is useful when GitHub Actions is not available. See
[DEPLOY.md](DEPLOY.md) for the full walkthrough, including the startup command the web app
needs:

```
gunicorn --bind=0.0.0.0 --timeout 600 app:app
```

## Layout

```
index.html, education.html, experience.html, projects.html, certifications.html, contact.html
admin.html                 Password-protected editor for every section
app.py                     Flask app: static files, content API, admin session
content_schema.py          Definition of every editable collection and field
data/*.seed.json           Starting content, copied to the volume on first run
requirements.txt           Flask and gunicorn
assets/css/style.css       All styling, including both theme palettes
assets/js/main.js          Theme toggle, mobile nav, accordions, scroll reveal
assets/js/content.js       Renders every page section from the content API
assets/js/admin.js         Schema-driven admin editor
assets/js/background.js    3D motion background canvas
assets/img/*.svg           Illustrations, background scene and favicon
.github/workflows/         Deploy workflow from Azure Deployment Center
deploy-azure.sh            One-shot Azure provisioning and deployment
```

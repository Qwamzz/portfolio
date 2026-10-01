# Nii Yartey Gidiglo - Portfolio

Personal site for a cloud, security and data engineer. Flask renders the pages on the server
from a small JSON content store, so every section can be edited from a password-protected admin
page without touching code. Hosted on Azure App Service (Linux, Python).

Live site: https://portfoliosite-fuedesckb9cxe3cf.uksouth-01.azurewebsites.net

## Pages

| Route | Content |
| --- | --- |
| `/` | Name, role and introduction, a terminal summary (or portrait), certification and tooling ticker, headline numbers, capabilities, recent work, recent roles |
| `/experience` | Roles grouped by section, each with responsibilities |
| `/projects` | Delivery engagements, GitHub repositories and published writing |
| `/certifications` | Credentials grouped by category, with certificate and verification links |
| `/education` | Degrees, community work and learning |
| `/contact` | Email, phone, location, profiles and services |
| `/admin` | Password-protected editor for all of the above |

## Design

- **Type does the work.** Bricolage Grotesque for display, Geist for text, Geist Mono for labels,
  all from Google Fonts. Headlines run large with tight negative tracking.
- **Paper and ink, one signal colour.** Off-white `#f3f2ed` and near-black `#0e0e0f`, with lime
  `#c8f031` used only as a fill (ticker band, accent button, markers) - never as text on paper.
- **Hairlines, not cards.** Sections, tables and grids are divided by 1px rules. No gradients,
  blurs or drop shadows on content.
- **Light and dark themes**, following the operating system on first visit; the toggle stores
  the choice. Every text/background pair clears WCAG AA in both (lowest is 5.25:1).
- **Restrained motion:** reveal on scroll, a slow ticker, link and arrow nudges. All of it
  stops under `prefers-reduced-motion`, and nothing is hidden if JavaScript does not run.

## Editing the site

Sign in at `/admin`. Every section supports add, edit, delete and reorder:

| Page | Editable sections |
| --- | --- |
| Home | Intro (name, role line, introduction, availability, location, portrait), headline numbers, capabilities |
| All pages | Heading and introduction for each inner page |
| Education | Degrees, beyond the classroom |
| Experience | Roles and the section each belongs to |
| Projects | Selected work, GitHub repositories, writing |
| Certifications | Certifications (with certificate upload), recognition |
| Contact | Email, phone, location, profile links, services |

Uploading a portrait in *Home - intro* replaces the terminal panel on the home page with the
photo; ticking "Remove the current file" brings the terminal back.

The admin forms are generated from [content_schema.py](content_schema.py) - add a field there
and it appears in the editor and in the data passed to the templates.

The admin area is disabled until `ADMIN_PASSWORD` is set on the web app, and every write
endpoint requires that session. See [DEPLOY.md](DEPLOY.md#turning-on-the-site-admin).

### Content defaults and corrections

`data/content.seed.json` and `data/certifications.seed.json` seed the store on first run. When
the schema grows, fields and sections missing from an existing store are filled from the seed
at read time; anything already stored, including values deliberately left blank, wins.

[content_fixes.py](content_fixes.py) corrects starting content that is already in a live store.
Each correction names the exact text originally seeded and applies only while the stored value
still matches it, so nothing edited through `/admin` is ever overwritten.

## Running locally

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python app.py
```

The site is then at http://localhost:8000 (set `PORT` to change it). Local content is written to
`data/store/`, which is git-ignored. Set `ADMIN_PASSWORD` in the environment to try the admin.

## Deployment

Pushes to `main` deploy to the `portfoliosite` web app through
[.github/workflows/main_portfoliosite.yml](.github/workflows/main_portfoliosite.yml), the
workflow the Azure portal's Deployment Center generated. It signs in with federated
credentials, so no publish profile or password is stored. See [DEPLOY.md](DEPLOY.md) for the
startup command and app settings.

## Layout

```
app.py                     Flask app: page rendering, content API, admin session
content_schema.py          Every editable collection and field
templates/                 Jinja templates - base layout, one per page, admin, 404
data/*.seed.json           Starting content, copied to the volume on first run
assets/css/style.css       All styling, both themes
assets/js/theme.js         Applies the saved theme before first paint
assets/js/main.js          Theme toggle, mobile menu, reveal on scroll
assets/js/admin.js         Schema-driven admin editor
assets/img/                Favicons, touch icon and share card
content_fixes.py           Safe corrections to content already in a live store
tools/                     Share-card generator (needs Pillow; not a site dependency)
requirements.txt           Flask and gunicorn
deploy-azure.sh            One-shot Azure provisioning and deployment
.github/workflows/         Deploy workflow from Azure Deployment Center
```

## Hardening and metadata

- Only pages, `/assets/`, `/uploads/`, the API, `robots.txt` and `sitemap.xml` are served; source
  files, templates and seed data are not reachable over HTTP.
- Every response carries a Content-Security-Policy (scripts from this origin only, fonts from
  Google Fonts), HSTS, `X-Frame-Options: DENY`, `nosniff`, a referrer policy and a permissions
  policy. There is no inline script, so the policy needs no exceptions for it.
- Open Graph and Twitter tags with a 1200x630 share card (`assets/img/og.png`), a canonical URL
  per page, and touch icons. Regenerate the images with
  [tools/make_share_images.py](tools/make_share_images.py) if the name or focus changes.
- The first screen animates in with CSS alone; content further down is revealed on scroll and
  falls back to visible after 2.5 seconds if the script never loads.

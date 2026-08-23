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
| `projects.html` | Twelve delivery engagements with scope and outcome, plus writing links |
| `certifications.html` | Microsoft, AWS, Oracle, CNCF and ISO credentials |
| `contact.html` | Email, phone, location, social links and areas of work |

## Design

- Light and dark themes. The first visit follows the operating system preference; the toggle in
  the navigation bar overrides it and the choice is stored in `localStorage`.
- Responsive down to 375px, with a collapsing navigation menu below 900px.
- Illustrations are hand-written SVG in `assets/img/` - no external asset or font requests, so
  the site loads with no third-party dependencies.
- Scroll-reveal animations respect `prefers-reduced-motion`.

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
app.py                     Flask static-file server (WSGI entry point for App Service)
requirements.txt           Flask and gunicorn
assets/css/style.css       All styling, including both theme palettes
assets/js/main.js          Theme toggle, mobile nav, accordions, scroll reveal
assets/img/*.svg           Illustrations and favicon
.github/workflows/         Deploy workflow from Azure Deployment Center
deploy-azure.sh            One-shot Azure provisioning and deployment
```

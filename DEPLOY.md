# Deploying the portfolio to Azure App Service

The site is static HTML, CSS, JS and SVG. `app.py` is a thin Flask wrapper that gives Azure a
WSGI entry point, serves extensionless URLs, sets cache headers and exposes `/healthz`.

Target: **Linux App Service, Python 3.12**, started with

```
gunicorn --bind=0.0.0.0 --timeout 600 app:app
```

## Names used throughout

| Setting | Value |
| --- | --- |
| Resource group | `rg-yartey-portfolio` |
| App Service plan | `asp-yartey-portfolio` (Linux, F1 free tier) |
| Web app | `yartey-portfolio` |
| Region | `westeurope` |
| URL | `https://yartey-portfolio.azurewebsites.net` |

Change any of them by exporting `RESOURCE_GROUP`, `PLAN`, `APP_NAME`, `LOCATION` or `SKU`
before running `deploy-azure.sh`. If the web app name is taken globally, pick another one and
update `AZURE_WEBAPP_NAME` in `.github/workflows/azure-webapps.yml` to match.

## Option A - provision once, then deploy on every push (recommended)

1. Sign in to Azure:

   ```bash
   az login
   ```

   On a machine without a browser, use `az login --use-device-code` and complete the sign-in on
   another device.

2. Provision the infrastructure and print the publish profile:

   ```bash
   ./deploy-azure.sh provision
   ```

3. Store the publish profile as a repository secret so GitHub Actions can deploy:

   ```bash
   az webapp deployment list-publishing-profiles --name yartey-portfolio \
     --resource-group rg-yartey-portfolio --xml | gh secret set AZURE_WEBAPP_PUBLISH_PROFILE
   ```

4. Push to `main`. The workflow installs dependencies, smoke tests every route, zips the site
   and deploys it. Watch it with:

   ```bash
   gh run watch
   ```

## Option B - deploy straight from the command line

Useful for the first deployment or when GitHub Actions is unavailable:

```bash
./deploy-azure.sh
```

This provisions anything missing and then runs `az webapp up`, which zips the working
directory, builds it with Oryx and restarts the app.

## Free tier note

`F1` is free but limited to 60 CPU minutes per day and has no custom domain SSL. Move to `B1`
for a production-grade portfolio:

```bash
az appservice plan update --name asp-yartey-portfolio \
  --resource-group rg-yartey-portfolio --sku B1
```

## Verifying a deployment

```bash
curl -fsS https://yartey-portfolio.azurewebsites.net/healthz
curl -o /dev/null -s -w '%{http_code}\n' https://yartey-portfolio.azurewebsites.net/
```

Both should return `{"status":"ok"}` and `200`. Live logs:

```bash
az webapp log tail --name yartey-portfolio --resource-group rg-yartey-portfolio
```

## Custom domain

```bash
az webapp config hostname add --webapp-name yartey-portfolio \
  --resource-group rg-yartey-portfolio --hostname www.example.com
az webapp config ssl create --resource-group rg-yartey-portfolio \
  --name yartey-portfolio --hostname www.example.com
```

A managed certificate requires at least the `B1` tier and a `CNAME` record pointing at
`yartey-portfolio.azurewebsites.net`.

## Troubleshooting

- **Application Error on first load** - the free tier cold-starts slowly; wait ~30 seconds and
  reload. If it persists, check the startup command is set:
  `az webapp config show --name yartey-portfolio --resource-group rg-yartey-portfolio --query linuxFxVersion,appCommandLine`.
- **CSS or images 404** - confirm `assets/` was included in the deployment package; the
  workflow's zip step excludes only `.git`, `.github`, `.venv` and Python caches.
- **Deployment succeeds but the old site is served** - App Service caches aggressively at the
  edge; `az webapp restart` clears it.

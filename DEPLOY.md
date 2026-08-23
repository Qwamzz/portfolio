# Deploying the portfolio to Azure App Service

The site is static HTML, CSS, JS and SVG. `app.py` is a thin Flask wrapper that gives Azure a
WSGI entry point, serves extensionless URLs, sets cache headers and exposes `/healthz`.

Target: **Linux App Service, Python 3.12**, started with

```
gunicorn --bind=0.0.0.0 --timeout 600 app:app
```

## Current setup

| Setting | Value |
| --- | --- |
| Web app | `portfoliosite` |
| Runtime | Python 3.12 on Linux |
| URL | `https://portfoliosite.azurewebsites.net` |
| Deployment | GitHub Actions via Deployment Center |
| Workflow | [.github/workflows/main_portfoliosite.yml](.github/workflows/main_portfoliosite.yml) |

The web app was connected to this repository through the Azure portal's **Deployment Center**,
which generated the workflow above and added the federated-credential secrets
(`AZUREAPPSERVICE_CLIENTID_*`, `AZUREAPPSERVICE_TENANTID_*`, `AZUREAPPSERVICE_SUBSCRIPTIONID_*`)
to the repository. Every push to `main` builds and deploys automatically - no publish profile
or stored password involved.

Watch a deployment:

```bash
gh run watch
```

## Required App Service configuration

Two settings the deployment itself does not set:

1. **Startup Command** (Configuration -> General settings):

   ```
   gunicorn --bind=0.0.0.0 --timeout 600 app:app
   ```

2. **Application setting** (Configuration -> Application settings):

   ```
   SCM_DO_BUILD_DURING_DEPLOYMENT = 1
   ```

   Deployment Center normally adds this for you. It makes Oryx run
   `pip install -r requirements.txt` on the platform, which is how gunicorn and Flask get
   installed. Without it the app starts with no dependencies and returns an Application Error.

Save either setting and App Service restarts the app.

## Verifying a deployment

```bash
curl -fsS https://portfoliosite.azurewebsites.net/healthz
curl -o /dev/null -s -w '%{http_code}\n' https://portfoliosite.azurewebsites.net/
```

Expect `{"status":"ok"}` and `200`. Live logs:

```bash
az webapp log tail --name portfoliosite --resource-group <your-resource-group>
```

## Deploying from the command line instead

`deploy-azure.sh` provisions a resource group, plan and web app from scratch and deploys with
`az webapp up`. Useful for rebuilding the infrastructure elsewhere or when GitHub Actions is
unavailable:

```bash
az login
APP_NAME=portfoliosite RESOURCE_GROUP=<your-resource-group> ./deploy-azure.sh
```

It also applies the startup command and app setting listed above. Override `RESOURCE_GROUP`,
`PLAN`, `APP_NAME`, `LOCATION` or `SKU` with environment variables.

## Free tier note

`F1` is free but limited to 60 CPU minutes per day and cannot do custom-domain SSL. For a
production-grade portfolio move to `B1`:

```bash
az appservice plan update --name <your-plan> --resource-group <your-resource-group> --sku B1
```

## Custom domain

```bash
az webapp config hostname add --webapp-name portfoliosite \
  --resource-group <your-resource-group> --hostname www.example.com
az webapp config ssl create --resource-group <your-resource-group> \
  --name portfoliosite --hostname www.example.com
```

A managed certificate requires at least `B1` and a `CNAME` record pointing at
`portfoliosite.azurewebsites.net`.

## Troubleshooting

- **Application Error on first load** - the free tier cold-starts slowly; wait ~30 seconds and
  reload. If it persists, confirm the startup command:
  `az webapp config show --name portfoliosite --resource-group <your-resource-group> --query "[linuxFxVersion,appCommandLine]"`.
- **Default Azure welcome page still showing** - the first deployment has not finished, or it
  deployed while the startup command was still empty. Re-run the workflow after setting it.
- **CSS or images 404** - confirm `assets/` reached the web app; browse the file system under
  `https://portfoliosite.scm.azurewebsites.net/newui/fileManager`.
- **A deployment succeeds but the old site is served** - `az webapp restart` clears it.

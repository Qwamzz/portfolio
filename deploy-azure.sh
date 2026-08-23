#!/usr/bin/env bash
# Provision and deploy the portfolio to Azure App Service.
#
#   ./deploy-azure.sh              provision (if needed) and deploy the current directory
#   ./deploy-azure.sh provision    provision only, then print the publish profile for GitHub
#
# Requires the Azure CLI and an authenticated session (az login).

set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-yartey-portfolio}"
LOCATION="${LOCATION:-westeurope}"
PLAN="${PLAN:-asp-yartey-portfolio}"
APP_NAME="${APP_NAME:-yartey-portfolio}"
SKU="${SKU:-F1}"
RUNTIME="${RUNTIME:-PYTHON:3.12}"
STARTUP="gunicorn --bind=0.0.0.0 --timeout 600 app:app"

echo "Resource group : $RESOURCE_GROUP ($LOCATION)"
echo "App Service    : $APP_NAME on $PLAN ($SKU)"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
echo "Resource group ready."

if ! az appservice plan show --name "$PLAN" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
  az appservice plan create \
    --name "$PLAN" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku "$SKU" \
    --is-linux \
    --output none
fi
echo "App Service plan ready."

if ! az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
  az webapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$PLAN" \
    --runtime "$RUNTIME" \
    --output none
fi
echo "Web app ready."

az webapp config set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --startup-file "$STARTUP" \
  --http20-enabled true \
  --output none

az webapp config appsettings set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=1 WEBSITES_PORT=8000 \
  --output none
echo "Configuration applied."

if [ "${1:-deploy}" = "provision" ]; then
  echo
  echo "Publish profile - store this as the AZURE_WEBAPP_PUBLISH_PROFILE secret in GitHub:"
  az webapp deployment list-publishing-profiles \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --xml
  exit 0
fi

echo "Deploying current directory..."
az webapp up \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$PLAN" \
  --runtime "$RUNTIME" \
  --sku "$SKU" \
  --location "$LOCATION"

URL="https://${APP_NAME}.azurewebsites.net"
echo
echo "Deployed: $URL"
echo "Health check:"
curl -fsS "${URL}/healthz" && echo

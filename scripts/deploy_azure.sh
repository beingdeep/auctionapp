#!/usr/bin/env bash
set -euo pipefail

# Usage:
# ./scripts/deploy_azure.sh \
#   --subscription "<subscription-id-or-name>" \
#   --resource-group "rg-auction-dev" \
#   --location "eastus" \
#   --project "auctionapp" \
#   --env "dev" \
#   --postgres-password "<strong-password>"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --subscription) SUBSCRIPTION="$2"; shift 2 ;;
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    --env) ENVIRONMENT="$2"; shift 2 ;;
    --postgres-password) POSTGRES_PASSWORD="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

: "${SUBSCRIPTION:?--subscription is required}"
: "${RESOURCE_GROUP:?--resource-group is required}"
: "${LOCATION:?--location is required}"
: "${PROJECT:?--project is required}"
: "${ENVIRONMENT:?--env is required}"
: "${POSTGRES_PASSWORD:?--postgres-password is required}"

az account set --subscription "$SUBSCRIPTION"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

DEPLOYMENT_NAME="${PROJECT}-${ENVIRONMENT}-$(date +%Y%m%d%H%M%S)"

# Initial deploy with a placeholder image to create ACR and infra.
az deployment group create \
  --name "$DEPLOYMENT_NAME-bootstrap" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters projectName="$PROJECT" environment="$ENVIRONMENT" containerImage="mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" postgresAdminPassword="$POSTGRES_PASSWORD" >/dev/null

ACR_LOGIN_SERVER=$(az deployment group show --name "$DEPLOYMENT_NAME-bootstrap" --resource-group "$RESOURCE_GROUP" --query properties.outputs.acrLoginServer.value -o tsv)
IMAGE_TAG="${ACR_LOGIN_SERVER}/${PROJECT}:${ENVIRONMENT}-$(git rev-parse --short HEAD)"

# Build and push image from local source to ACR using Azure build service.
ACR_NAME="${ACR_LOGIN_SERVER%%.*}"
az acr build --registry "$ACR_NAME" --image "$IMAGE_TAG" .

# Redeploy with the actual app image.
az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters projectName="$PROJECT" environment="$ENVIRONMENT" containerImage="$IMAGE_TAG" postgresAdminPassword="$POSTGRES_PASSWORD" >/dev/null

APP_URL=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.containerAppUrl.value -o tsv)
PG_FQDN=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.postgresFqdn.value -o tsv)

echo "Deployment complete"
echo "Container App URL: ${APP_URL}"
echo "PostgreSQL FQDN: ${PG_FQDN}"

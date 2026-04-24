#!/usr/bin/env bash
set -euo pipefail

# Deploy foundational Azure resources (ACR, ACA env/app, PostgreSQL, Redis).
# Usage:
# ./scripts/deploy_infra.sh \
#   --subscription "<subscription-id-or-name>" \
#   --resource-group "rg-auction-dev" \
#   --location "eastus" \
#   --project "auctionapp" \
#   --env "dev" \
#   --postgres-password "<strong-password>" \
#   --django-secret "<django-secret-key>"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --subscription) SUBSCRIPTION="$2"; shift 2 ;;
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    --env) ENVIRONMENT="$2"; shift 2 ;;
    --postgres-password) POSTGRES_PASSWORD="$2"; shift 2 ;;
    --django-secret) DJANGO_SECRET="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

: "${SUBSCRIPTION:?--subscription is required}"
: "${RESOURCE_GROUP:?--resource-group is required}"
: "${LOCATION:?--location is required}"
: "${PROJECT:?--project is required}"
: "${ENVIRONMENT:?--env is required}"
: "${POSTGRES_PASSWORD:?--postgres-password is required}"
: "${DJANGO_SECRET:?--django-secret is required}"

az account set --subscription "$SUBSCRIPTION"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

DEPLOYMENT_NAME="${PROJECT}-${ENVIRONMENT}-infra-$(date +%Y%m%d%H%M%S)"
PLACEHOLDER_IMAGE="mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"

az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters \
    projectName="$PROJECT" \
    environment="$ENVIRONMENT" \
    containerImage="$PLACEHOLDER_IMAGE" \
    postgresAdminPassword="$POSTGRES_PASSWORD" \
    djangoSecretKey="$DJANGO_SECRET" >/dev/null

mkdir -p .azure
OUTPUT_FILE=".azure/${PROJECT}-${ENVIRONMENT}.env"

ACR_LOGIN_SERVER=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.acrLoginServer.value -o tsv)
CONTAINER_APP_NAME=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.containerAppName.value -o tsv)
CONTAINER_APP_URL=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.containerAppUrl.value -o tsv)

cat > "$OUTPUT_FILE" <<ENV
SUBSCRIPTION="$SUBSCRIPTION"
RESOURCE_GROUP="$RESOURCE_GROUP"
PROJECT="$PROJECT"
ENVIRONMENT="$ENVIRONMENT"
ACR_LOGIN_SERVER="$ACR_LOGIN_SERVER"
CONTAINER_APP_NAME="$CONTAINER_APP_NAME"
CONTAINER_APP_URL="$CONTAINER_APP_URL"
ENV

echo "Infrastructure deployment complete"
echo "Saved deployment outputs to: $OUTPUT_FILE"
echo "Container App URL (placeholder image): $CONTAINER_APP_URL"

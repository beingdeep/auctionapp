#!/usr/bin/env bash
set -euo pipefail

# Build/push the current app image and update existing Container App.
# Usage:
# ./scripts/deploy_app.sh --env-file .azure/auctionapp-dev.env

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

: "${ENV_FILE:?--env-file is required}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE"
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${SUBSCRIPTION:?SUBSCRIPTION missing in env file}"
: "${RESOURCE_GROUP:?RESOURCE_GROUP missing in env file}"
: "${ACR_LOGIN_SERVER:?ACR_LOGIN_SERVER missing in env file}"
: "${CONTAINER_APP_NAME:?CONTAINER_APP_NAME missing in env file}"
: "${PROJECT:?PROJECT missing in env file}"
: "${ENVIRONMENT:?ENVIRONMENT missing in env file}"

az account set --subscription "$SUBSCRIPTION"

IMAGE_TAG="${ACR_LOGIN_SERVER}/${PROJECT}:${ENVIRONMENT}-$(git rev-parse --short HEAD)"
ACR_NAME="${ACR_LOGIN_SERVER%%.*}"

az acr build --registry "$ACR_NAME" --image "$IMAGE_TAG" .

az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$IMAGE_TAG" >/dev/null

APP_FQDN=$(az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)

echo "Application deployment complete"
echo "Live URL: https://${APP_FQDN}"

# Local Tournament Player Auction System

This repository contains an MVP backend scaffold for a local cricket/football player auction platform.

## Stack
- Django + Django REST Framework
- Django Channels (ready for websocket integration)
- PostgreSQL-compatible models (SQLite default for local development)
- Azure Container Apps + Azure Database for PostgreSQL (infra templates included)

## Apps
- `accounts`: role-based user model (`admin`, `captain`, `auctioneer`)
- `tournaments`: tournament configuration and status
- `players`: player master data and sold/unsold state
- `teams`: team profile and purse balance
- `auction`: rounds, bids, validation, winner finalization logic
- `reports`: summary query helpers
- `realtime`: websocket consumer scaffold for future live events

## Quick start (local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

## Azure deployment (Container Apps + PostgreSQL)
### What gets deployed
- Azure Container Registry (build/push image)
- Log Analytics Workspace
- Container Apps Environment
- Container App (public ingress)
- Azure Database for PostgreSQL Flexible Server + database + firewall rule for Azure services

### Deploy from local machine
1. Make sure Azure CLI is installed and you are logged in (`az login`).
2. Run:

```bash
./scripts/deploy_azure.sh \
  --subscription "<subscription-id-or-name>" \
  --resource-group "rg-auction-dev" \
  --location "eastus" \
  --project "auctionapp" \
  --env "dev" \
  --postgres-password "<strong-password>"
```

The script bootstraps infra, builds/pushes the current repo image to ACR, then redeploys the Container App with the pushed image.

## Infra files
- `infra/main.bicep`: full Azure infrastructure template.
- `scripts/deploy_azure.sh`: end-to-end Azure CLI deployment script.

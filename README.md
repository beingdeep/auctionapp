# Local Tournament Player Auction System

This repository contains an MVP backend scaffold for a local cricket/football player auction platform.

## Stack
- Django + Django REST Framework
- Django Channels (ready for websocket integration)
- PostgreSQL-compatible models (SQLite default for local development)
- Azure Container Apps + Azure Database for PostgreSQL + Azure Cache for Redis (infra templates included)

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

## Azure deployment (internet-accessible app)
### What gets deployed
- Azure Container Registry (build/push image)
- Log Analytics Workspace
- Container Apps Environment
- Container App with external ingress (public URL)
- Azure Database for PostgreSQL Flexible Server + database + firewall rule for Azure services
- Azure Cache for Redis (for Channels/websocket scaling)

### 1) Deploy infrastructure
```bash
./scripts/deploy_infra.sh \
  --subscription "<subscription-id-or-name>" \
  --resource-group "rg-auction-dev" \
  --location "eastus" \
  --project "auctionapp" \
  --env "dev" \
  --postgres-password "<strong-password>" \
  --django-secret "<django-secret-key>"
```

This creates infra and writes output variables to `.azure/<project>-<env>.env`.

### 2) Deploy/update application image
```bash
./scripts/deploy_app.sh --env-file .azure/auctionapp-dev.env
```

This builds from your local source, pushes to ACR, and updates Container App to the new image.

### 3) One-command end-to-end deploy
```bash
./scripts/deploy_all.sh \
  --subscription "<subscription-id-or-name>" \
  --resource-group "rg-auction-dev" \
  --location "eastus" \
  --project "auctionapp" \
  --env "dev" \
  --postgres-password "<strong-password>" \
  --django-secret "<django-secret-key>"
```

After deployment completes, the app is reachable from the public internet using the Container App URL printed by the script.

## Infra files
- `infra/main.bicep`: full Azure infrastructure template.
- `scripts/deploy_infra.sh`: deploys infra and stores output variables.
- `scripts/deploy_app.sh`: builds + pushes image and updates live app.
- `scripts/deploy_all.sh`: runs infra and app deployment together.

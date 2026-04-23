# Local Tournament Player Auction System

This repository contains an MVP backend scaffold for a local cricket/football player auction platform.

## Stack
- Django + Django REST Framework
- Django Channels (ready for websocket integration)
- PostgreSQL-compatible models (SQLite default for local development)

## Apps
- `accounts`: role-based user model (`admin`, `captain`, `auctioneer`)
- `tournaments`: tournament configuration and status
- `players`: player master data and sold/unsold state
- `teams`: team profile and purse balance
- `auction`: rounds, bids, validation, winner finalization logic
- `reports`: summary query helpers
- `realtime`: websocket consumer scaffold for future live events

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

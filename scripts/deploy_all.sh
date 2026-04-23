#!/usr/bin/env bash
set -euo pipefail

ARGS=("$@")
PROJECT=""
ENVIRONMENT=""

for ((i=1; i<=$#; i++)); do
  if [[ "${!i}" == "--project" ]]; then
    next=$((i+1))
    PROJECT="${!next}"
  fi
  if [[ "${!i}" == "--env" ]]; then
    next=$((i+1))
    ENVIRONMENT="${!next}"
  fi
done

scripts/deploy_infra.sh "${ARGS[@]}"

if [[ -z "$PROJECT" || -z "$ENVIRONMENT" ]]; then
  echo "Could not infer --project/--env from arguments"
  exit 1
fi

scripts/deploy_app.sh --env-file ".azure/${PROJECT}-${ENVIRONMENT}.env"

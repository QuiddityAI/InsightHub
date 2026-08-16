#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"


echo "==> Rebuilding and restarting prod backend + webserver..."
docker compose -f docker-compose-staging.yaml --env-file .env \
  up -d --no-deps --build backend-staging webserver-staging

echo "==> Done. Prod stack running on port 55440. (migrations run automatically on startup)"
docker compose -f docker-compose-staging.yaml --env-file .env \
  ps backend-staging webserver-staging

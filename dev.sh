#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Rebuilding and restarting dev backend + webserver..."
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.gpu.yaml \
  -f docker-compose.override.pdferret.yaml \
  -f docker-compose.override.import.yaml \
  -f docker-compose.override.dev.yaml \
  --env-file .env \
  up -d --no-deps --build backend webserver

echo "==> Done. Dev stack running on port 55140. (migrations run automatically on startup)"
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.gpu.yaml \
  -f docker-compose.override.pdferret.yaml \
  -f docker-compose.override.import.yaml \
  -f docker-compose.override.dev.yaml \
  ps backend webserver

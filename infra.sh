#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Starting shared infrastructure..."
docker compose up -d \
  qdrant \
  opensearch \
  postgres \
  infinity-model-server \
  gpu-utility-server \
  opensearch-dashboards \
  pdferret \
  tika

echo "==> Done."
docker compose ps qdrant opensearch postgres infinity-model-server gpu-utility-server

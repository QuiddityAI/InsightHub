#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"


echo "==> Rebuilding and restarting prod backend..."
# The backend reads .env from a bind-mounted *file* via load_dotenv() in
# manage.py. Editing that file replaces its inode, so a running container keeps
# reading the old contents and a plain `up -d` will not notice: compose only
# recreates when the service definition changes, and these variables are read
# inside the container rather than interpolated by compose. --force-recreate
# guarantees the current .env is what the backend actually sees.
docker compose -f docker-compose-staging.yaml --env-file .env \
  up -d --no-deps --build --force-recreate backend-staging

echo "==> Rebuilding and restarting webserver + TLS terminator..."
docker compose -f docker-compose-staging.yaml --env-file .env \
  up -d --no-deps --build webserver-staging tls-terminator certbot-renew

echo "==> Done. HTTP on 55440, TLS on 55443 (55444 with PROXY protocol), loopback only."
echo "    (migrations run automatically on startup)"
docker compose -f docker-compose-staging.yaml --env-file .env \
  ps backend-staging webserver-staging tls-terminator certbot-renew

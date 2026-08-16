#!/bin/sh
# Runs as part of the nginx image's entrypoint, before nginx starts.
#
# Reloads nginx every 6 hours so that a certificate renewed by the certbot
# container is picked up without restarting the proxy. This has to be a
# /docker-entrypoint.d/ script rather than a `command:` override, because the
# image only runs its init scripts (including the envsubst template step) when
# the command it is given starts with "nginx".
( while :; do sleep 21600; nginx -s reload 2>/dev/null || true; done ) &

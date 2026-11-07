#!/bin/sh
# Starts the portal on a host (Render, Railway, Fly.io, Docker).
# DEMO_PASSWORD is the password of the demo officer accounts. It is required.
set -e
if [ -z "$DEMO_PASSWORD" ] || [ ${#DEMO_PASSWORD} -lt 8 ]; then
  echo "Set DEMO_PASSWORD (at least 8 characters) in the host's environment settings." >&2
  exit 1
fi
python portal/manage.py seed-demo --password "$DEMO_PASSWORD" > /dev/null
if [ "$SEED_SAMPLE" = "1" ]; then
  python portal/manage.py seed-sample
fi
exec python portal/server.py

#!/bin/sh
# Starts the portal on a host (Render, Railway, Fly.io, Docker).
# DEMO_PASSWORD is the password of the demo officer accounts. It is required.
set -e
if [ -z "$DEMO_PASSWORD" ] || [ ${#DEMO_PASSWORD} -lt 8 ]; then
  echo "Set DEMO_PASSWORD (at least 8 characters) in the host's environment settings." >&2
  exit 1
fi
# With DATABASE_URL set, bring back the data saved before the last restart (nothing happens without it).
python portal/manage.py restore
python portal/manage.py seed-demo --password "$DEMO_PASSWORD" > /dev/null
if [ "$SEED_SAMPLE" = "1" ]; then
  python portal/manage.py seed-sample
else
  # No invented demo data: remove any that an earlier start added. Real complaints are never touched.
  python portal/manage.py purge-sample
fi
exec python portal/server.py

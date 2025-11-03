#!/usr/bin/env bash
# Script to run migrations for default, brise and pavimentos
set -e

if [ -z "$DJANGO_SETTINGS_MODULE" ]; then
  export DJANGO_SETTINGS_MODULE=config.settings
fi

echo "Running migrations for default DB"
python manage.py migrate --database=default

if python - <<'PY'
from django.conf import settings
print('brise' in settings.DATABASES)
PY
then
  echo "Running migrations for brise"
  python manage.py migrate --database=brise
else
  echo "No 'brise' database configured; skipping"
fi

if python - <<'PY'
from django.conf import settings
print('pavimentos' in settings.DATABASES)
PY
then
  echo "Running migrations for pavimentos"
  python manage.py migrate --database=pavimentos
else
  echo "No 'pavimentos' database configured; skipping"
fi


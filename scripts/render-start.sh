#!/usr/bin/env bash
set -euo pipefail

# Free Render services have no pre-deploy command or shell. Apply additive
# migrations before accepting traffic. Never seed or reset data automatically.
uv run --no-sync python manage.py migrate --noinput
exec uv run --no-sync gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 2 \
    --access-logfile - --error-logfile -

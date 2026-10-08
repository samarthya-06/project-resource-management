# Render Free deployment

Use one Free Python web service and one Free PostgreSQL database in Singapore.
The database is separate from the local development database. It expires after
30 days; export needed records before expiry. The web service sleeps when idle.

## Web service configuration

- Repository: `samarthya-06/project-resource-management`, branch `main`.
- Runtime: Python 3. Root Directory: blank. Instance: Free.
- Build Command: `bash scripts/render-build.sh`.
- Start Command: `bash scripts/render-start.sh`.
- Set auto-deploy to manual during initial setup if you want to review each release.

Environment variables (enter secrets directly in Render, never commit them):

| Key | Value |
| --- | --- |
| `DJANGO_SECRET_KEY` | Render's Generate button; retain across deployments |
| `DJANGO_DEBUG` | `False` |
| `DATABASE_URL` | Database Info → Internal Database URL, with `?sslmode=require` appended; if it already has a query string, append `&sslmode=require` |
| `DJANGO_SECURE_HSTS_SECONDS` | `3600` |

Render supplies `RENDER_EXTERNAL_HOSTNAME` and `PORT`. The application adds that
exact hostname to allowed hosts and HTTPS CSRF origins, trusts Render's forwarded
HTTPS header, and redirects plain HTTP to HTTPS. Do not manually set the Render
hostname variable on untrusted infrastructure. Custom domains require
`DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` additions.

The checked-in `.python-version` selects Python 3.12. `uv sync --locked --no-dev`
installs the committed dependency versions. WhiteNoise serves collected, compressed,
versioned static files. Gunicorn runs one worker with two threads on the assigned port.
There is no live timer, background worker or persistent upload storage.

## Migration and demo setup

Startup applies existing additive migrations before Gunicorn accepts traffic. A
failed migration prevents startup and must be investigated; never reset the database.
This is a single-instance demo deployment, not a multi-instance migration strategy.
Builds and starts never create demo passwords or seed data automatically.

Free Render services have no interactive shell. To seed the hosted demo explicitly,
use a terminal on your computer in this repository, after the first successful deploy.
Use the database's **External Database URL** for this local command, with TLS required.
These temporary variables apply only to the management command, not the hosted server:

```bash
read -rs 'DATABASE_URL?Paste External Database URL with sslmode=require: '
export DATABASE_URL
read -rs 'DEMO_PASSWORD?Choose a strong hosted demo password: '
export DEMO_PASSWORD
DJANGO_DEBUG=True uv run python manage.py seed_demo
unset DATABASE_URL DEMO_PASSWORD
```

The `read` prompts shown above use macOS zsh. Passwords are not echoed or added to
shell history. The explicit command targets the remote database; double-check the
URL privately before running. Existing records/passwords are preserved. Demo accounts
are intentionally preconfigured without first-password gating; newly provisioned
accounts and password resets still require password change. The hosted web service
must keep `DJANGO_DEBUG=False`. Share credentials privately and do not publish a
privileged demo password in README or screenshots.

## Verification and troubleshooting

Before deployment:

```bash
uv sync --locked
uv run python manage.py collectstatic --noinput
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest
uv run ruff check .
```

After deployment, check HTTPS login, CSS/fonts, password change, POST logout,
Admin account management, Manager project/member/task operations, Employee
start/time/edit/complete, completed locks, foreign-resource denial and reports.
Check logs for migration/startup failures. Confirm data persists after redeployment.
Do not treat local tests as hosted verification. Local manual cases remain separate.

If database connections fail, check region, credentials and TLS URL. If login POST
fails CSRF, check the external hostname and forwarded HTTPS configuration. Never
resolve these failures with `DEBUG=True`, wildcard hosts or disabled CSRF.

References: [Render Django guide](https://render.com/docs/deploy-django),
[free service limits](https://render.com/docs/free),
[Python version selection](https://render.com/docs/python-version).

## Executed local evidence (8 October 2026)

- `collectstatic --noinput`: 160 files copied, 462 post-processed.
- Django check: no issues. Migration drift: no changes detected.
- Ruff: passed. Both shell scripts passed `bash -n`.
- Full PostgreSQL/browser regression run: 273 passed, one new deployment test
  failed because its test override did not recalculate secure-cookie settings.
  After correcting that test, all four deployment tests passed (0.33 seconds).
  All 270 existing tests passed in the full run (79.21 seconds); application code
  did not change after that run. Ruff passed again after the test correction.
- Gunicorn with `DEBUG=False`: login and workspace CSS both returned HTTP 200.
- `check --deploy` with simulated Render hostname and one-hour HSTS: only W005
  (include subdomains) and W021 (preload) warnings. These optional policies are
  intentionally disabled for the temporary hosted demo.
- Live Render build, migrations, TLS/database connectivity and hosted workflows
  have not yet been executed. No remote database was modified during preparation.

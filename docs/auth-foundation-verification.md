# Authentication foundation — executed verification

Date: 7 October 2026. Scope: the initial Django/PostgreSQL/account/authentication milestone.

## Environment and database

- Locked environment synchronized successfully: Python 3.12, Django 5.2.18, DRF 3.18.3,
  psycopg 3.3.6. Django 5.2 is an LTS series supported by DRF:
  https://docs.djangoproject.com/en/5.2/releases/5.2/ and
  https://www.django-rest-framework.org/ .
- Existing local PostgreSQL 17.11 server inspected. Created dedicated `prms_b532`
  role/database; verified connection as that role. Local role has CREATEDB for test
  databases, not superuser privileges. Credentials generated in ignored `.env`.
- Applied Django auth/admin/contenttypes/sessions and custom User initial migrations.
- Explicit `seed_demo` created seven accounts. Repeating it preserved all seven.

## Executed checks

| Check | Actual result |
| --- | --- |
| uv sync --locked | Passed (writable project cache selected) |
| python manage.py migrate | All initial migrations applied to PostgreSQL |
| python manage.py check | No issues |
| python manage.py makemigrations --check --dry-run | No changes detected, PostgreSQL history checked |
| pytest -q | 31 passed in 13.30 seconds, separate PostgreSQL test database |
| ruff check accounts config tests scripts | Passed |
| ruff format --check accounts config tests scripts | 23 files already formatted |
| git diff --check | Passed |
| python scripts/verify_auth_browser.py | All desktop authentication smoke checks passed |

All Python commands used the uv-managed environment. Sandbox restrictions required
access for PostgreSQL loopback connections, dependency/font downloads and Chromium;
no SQLite substitution was used.

Automated backend checks cover password hashing; all three roles and forged role
input; superuser bootstrap; unique identifiers; database role/privilege constraints;
anonymous/inactive access; old-session deactivation; generic errors and cleared
password fields; real CSRF on login, password change and logout; POST-only logout;
external redirect rejection; initial-password page/API/Admin gate; password strength,
confirmation and old-password failures; current-session retention/other-session
invalidation; read-only identity scope; normal-user Admin denial; administrative account
creation/reset; seed preservation and production refusal.

The first run found an incorrect reference to a lowercase environment helper through
Django settings (30 passed, one failed). Changed the command to consume the uppercase
`DEMO_PASSWORD` setting and retested: all 31 passed. The development seed then ran
successfully twice.

## Browser evidence

Chromium at 1440 × 900 verified the login card width (440px), bundled font CSS,
no horizontal overflow, Show/Hide toggle, generic failed-login message, preserved
identifier/cleared password, all three role logins/current-user identities, password
page access, successful POST sign-out, and inactive-account denial.

- `docs/evidence/authentication/login.png`: initial working login.
- `docs/evidence/authentication/login-error.png`: failed login with visible keyboard focus.

The failed-login screenshot was visually reviewed: consistent spacing, readable labels,
clear hierarchy/contrast, aligned fields/buttons and no clipped content. The layout uses
Paper-exported login dimensions; font uses the application contract's IBM Plex Sans.
Full Paper screen parity and complete keyboard/contrast auditing are not claimed.

These checks are automated evidence for authentication. Required assignment manual
cases, project workflows, SQL/report verification and clean-checkout rehearsal remain
pending; see `known-limitations.md`.

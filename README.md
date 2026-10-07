# Project & Resource Management System

Django take-home assignment for Piiritu Innovations. Implemented: PostgreSQL,
custom role-aware accounts, session authentication, password change, project data models,
protected relationships, explicit data validation and deterministic demo data.
Shared permission operations and scoped reads are implemented; resource APIs, reports and the designed application screens remain pending.

## Stack

Python 3.12, Django 5.2.18, DRF 3.18.3, PostgreSQL 17 (local verification), psycopg 3.3.6.
Dependencies are locked in `uv.lock`. Frontend: Django templates, HTML/CSS and plain JavaScript.
IBM Plex Sans is bundled with its SIL Open Font License in `static/fonts/`.

## Setup

Install Python 3.12, uv and a running PostgreSQL server. From the repository root:

```bash
uv sync --locked
cp .env.example .env
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated secret in `DJANGO_SECRET_KEY`; replace the database password and
all other placeholders in `.env`. Keep `.env` private and outside version control.
For local HTTP development set `DJANGO_DEBUG=True` and allow `localhost,127.0.0.1`.
With debug disabled, cookies require HTTPS. Environment variables take precedence over `.env`.

Connect as a PostgreSQL administrator (adjust your administrator username/host):

```bash
psql -h 127.0.0.1 -U YOUR_POSTGRES_ADMIN -d postgres
```

Run once, using the same names/password as your `.env`:

```sql
CREATE ROLE project_user LOGIN CREATEDB PASSWORD 'YOUR_LOCAL_DATABASE_PASSWORD';
CREATE DATABASE project_resource OWNER project_user;
```

`CREATEDB` is for local pytest test-database creation; this application role has no
superuser or role-creation privileges. Tests use `test_<DB_NAME>` and do not reset
the development database. If those names already exist, inspect/reuse the intended
project resources rather than deleting or overwriting them.

Then:

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/login/. `createsuperuser` creates the initial Admin account.
The authenticated landing page is currently a foundation page, with password change
and POST sign-out. The full Paper Overview and workflow screens are the next milestone.

## Accounts and authentication

- One login for all roles: Admin, Project Manager, Employee. Login identifier is the
  unique Django username (demo usernames resemble email addresses). Identifiers are
  case-sensitive; email is optional contact data, not a separate login identifier.
- Django handles password hashing, session authentication and inactive-user checks.
  Anonymous pages redirect to login; anonymous `/api/` requests return 403 with
  SessionAuthentication. Login errors do not reveal whether an account exists/is inactive.
- New accounts default to a required password change. Until changed, they may access
  only login, password change and POST logout; API access returns 403. A password change
  requires the old password, matching confirmation and Django strength validation
  (minimum ten characters). It retains the current session and invalidates other sessions.
- Bootstrap Admins can provision accounts at `/admin/accounts/user/add/`, select the
  stored role and give initial credentials privately. There is no public signup/email
  delivery. The application Employees create/edit screens remain pending.
- Development account administration requires an active Django superuser with the Admin
  role. Manager/Employee roles cannot hold `is_staff` or `is_superuser`; database checks
  enforce this. User deletion is disabled in Django Admin; deactivate instead. Resetting
  another user's password there restores the initial-password requirement.
- Application Admin is a business role; Django superuser is a separate administrative
  privilege. Only bootstrap/development superusers use this administrative interface.
- Login, password change and logout require CSRF tokens. Logout accepts POST only.
  A same-origin JavaScript request must send the session cookie and `X-CSRFToken` on
  future state-changing API requests. There is no token/JWT authentication configured.

## Optional development demo data

Set a strong `DEMO_PASSWORD` in `.env`, then explicitly run:

```bash
uv run python manage.py seed_demo
```

| Identifier | Role | Status |
| --- | --- | --- |
| admin@demo.local | Admin (development superuser) | Active |
| neha@demo.local | Project Manager | Active |
| arjun@demo.local | Project Manager | Active |
| asha@demo.local | Employee | Active |
| ravi@demo.local | Employee | Active |
| meera@demo.local | Employee | Inactive |
| dev@demo.local | Employee | Active, unassigned |

New demo accounts share your chosen `DEMO_PASSWORD`; credentials are never printed by
the seed command or shown on the login page. Demo accounts skip the initial-password
requirement for rehearsal. Repeating the command preserves existing accounts and
passwords. It refuses to run when debug is disabled and never runs automatically.
It also creates the following project fixtures on first use:

| Manager | Project | Tasks | Completed | Logged hours |
| --- | --- | --- | --- | --- |
| Neha | Client Website Redesign | 6 | 2 | 12 |
| Neha | Employee Onboarding Portal | 5 | 2 | 12 |
| Neha | Internal Knowledge Base | 0 | 0 | 0 |
| Arjun | Operations Handbook | 1 | 0 | 0 |

Neha's totals match the Paper handoff: three projects, seven unfinished tasks,
four completed tasks and 24 hours. Website contributors are Asha 420 minutes and
Ravi 300 minutes. Asha's own totals are two tasks in each status and 13 hours.
The fourth project belongs to the second manager for isolation testing; it adds no
hours to Neha's totals. Meera is inactive and unassigned; Dev is active and unassigned
on a fresh seed. The complete seed creates 7 accounts, 4 projects, 5 memberships,
12 tasks and 7 time entries. Work entries use 06 Oct 2026, or the current date if
the command is run earlier, so the demo never creates future-dated time.

Stable internal `Project.demo_key` values identify demo roots. Existing demo projects
and their entire contents are skipped on subsequent runs: names, dates, assignments,
statuses, time notes/minutes, deleted children and account changes are preserved.
Normal user-created projects with matching display names are not adopted or overwritten.
If an existing account's role/activity conflicts with a missing project's new data,
validation fails and the transaction rolls back; the command does not repair/reset accounts.
Deleting an entire demo project removes its key; an explicit later seed can recreate it.
Expected sample totals apply to fresh fixtures; rerunning the seed does not restore totals
after user edits. There is no destructive reset or force-refresh option.

## Project data rules and deletion

`Project` belongs to a Project Manager; `ProjectMembership` links an Employee to a
project; `Task` belongs to that project and a member assignee; `TimeEntry` preserves
its task and original contributor independently of later reassignment.

Ordinary model saves explicitly validate roles/activity, membership, required fields,
project date ordering, forward task status changes and positive whole-minute entries
(1–1440, no future dates). Database constraints independently protect row invariants.
Bulk ORM updates/inserts and raw SQL bypass cross-table validation and must not be used
as future application write paths. See `docs/schema.md` for exact field definitions,
constraints, lock order and the distinction between data validation and actor permissions.

All dependent foreign keys use PROTECT. Projects with team/tasks, tasks with time,
and referenced users cannot be casually deleted. Membership removal is blocked by
unfinished assignments; completed tasks and original contribution history survive removal.
Empty projects, tasks without time and leaf time entries are deletable only at the
trusted data layer for now; completed-record/role permissions require the next service phase.
The four new models are not exposed as writable resources in Django Admin.

Use additive migrations. `projects/0001_initial.py` adds new tables and depends on the
existing User; `accounts/0001_initial.py` remains unchanged. Inspect `migrate --plan`
before applying to an existing database. Never delete applied migrations or reset records.

The prepared local worktree uses its own `prms_b532` database/role. Its generated local
credentials and demo password are in the ignored `.env`; they are not repository defaults.

## Checks

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest
uv run ruff check accounts config projects/models.py projects/demo.py projects/migrations tests scripts
uv run ruff format --check accounts config projects/models.py projects/demo.py projects/migrations tests scripts
```

PostgreSQL must be available and the database role needs permission to create a test
database. Do not switch tests to SQLite. In a filesystem sandbox, a writable uv cache
can be selected with `--cache-dir .cache/uv`; this does not change the environment or lockfile.

### Desktop browser check

Install Chromium once and run the smoke script while the development server is running:

```bash
uv run playwright install chromium
uv run python scripts/verify_auth_browser.py
```

Run `seed_demo` first and keep its accounts/passwords unchanged for this script. It uses
`DEMO_PASSWORD` from your local environment, tests login for all three roles, checks
Show/Hide and failed/inactive login, visits password change, verifies POST logout and
saves 1440 × 900 screenshots in `docs/evidence/authentication/`. It does not submit a
password change or modify account data. Optional `AUTH_BASE_URL` selects another local
server address. This is an automated browser check, not manual-case evidence.

See `docs/auth-foundation-verification.md` and `docs/project-data-verification.md` for
executed checks, `docs/api.md` for current endpoints, `docs/schema.md` for the models,
and `docs/known-limitations.md`.
The Paper design handoff is in `docs/paper-ui-handoff.md`. Desktop-only design artifacts
were requested by the user. The complete assignment and required manual evidence are pending.

## Shared business operations (Phase 2)

`projects/services.py` handles authorized projects, membership, tasks and time;
`projects/selectors.py` scopes reads; `accounts/services.py` handles Admin account
management. Future views/APIs must use these functions. See
[the operation contract](docs/business-rules.md) for editable fields, completed-work
corrections, private notes, role-change prerequisites and transaction behavior.
Existing roles are read-only in Django Admin; guarded application operations change them.

Run the focused permission journey and rejection tests with:

```bash
uv run pytest tests/test_business_operations.py -q
```

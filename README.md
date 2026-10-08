# Project & Resource Management System

Django take-home assignment for Piiritu Innovations. Implemented: PostgreSQL,
custom role-aware accounts, session authentication, password change, project data models,
protected relationships, explicit data validation and deterministic demo data.
Shared operations, scoped REST APIs/reports and the complete Phase 4A/4B desktop
workspace, task management and time tracking are implemented.

## Stack

Python 3.12, Django 5.2.18, DRF 3.18.3, PostgreSQL 17 (local verification), psycopg 3.3.6.
Dependencies are locked in `uv.lock`. Frontend: Django templates, HTML/CSS and plain JavaScript.
IBM Plex Sans is bundled with its SIL Open Font License in `static/fonts/`.

## Setup

For the interview demo deployment, see [Render Free setup](docs/render-deployment.md).
It covers the exact build/start commands, secrets, migrations and explicit hosted seeding.

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
The authenticated landing page is the role-scoped Overview. The desktop workspace includes account, project/team management and project reports, with task assignment, time recording, completion, password change and POST sign-out.

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
- Application Admins provision, edit and deactivate accounts through `/employees/`.
  Give initial credentials privately; new/reset accounts must change their password.
  There is no public signup/email delivery. `/admin/` is optional bootstrap administration.
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
Shared services and REST APIs authorize safe deletion of empty projects and eligible
tasks/time entries; dependent history is protected and completed-work locks apply.
The Phase 4A project UI implements create/edit/team operations, without a delete action.
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
uv run ruff check accounts config projects tests scripts
uv run ruff format --check accounts config projects tests scripts
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

## REST resources and reports (Phase 3)

See [API documentation](docs/api.md) for the exact account/project/membership/task/time
routes, session/CSRF instructions, field restrictions, filters, pagination and errors.
Reports and Overview use current scoped database values and original time contributors.
No additional project migration is required for this phase.

```bash
uv run pytest tests/test_resource_api.py -q
uv run python manage.py shell -c 'from scripts.verify_project_reports import verify; print(verify())'
```

The comparison executes [read-only PostgreSQL queries](sql/project_reports.sql) against
existing data without reseeding/resetting it. See `docs/api-verification.md` for actual
HTTP/test and SQL comparison evidence. Task/time application screens are implemented in Phase 4B.

## Desktop workspace (Phase 4A)

| Route | Screen and access |
| --- | --- |
| `/` | Overview; all roles, authorized scope only |
| `/employees/` | Account list/search/status filter; Admin only |
| `/employees/create/` | Account creation; Admin only |
| `/employees/<id>/edit/` | Account edit/optional password reset; Admin only |
| `/employees/<id>/deactivate/` | Confirmation then POST deactivation; Admin only |
| `/projects/` | Scoped project list/name search; all roles |
| `/projects/create/` | Admin or Manager project creation |
| `/projects/<id>/edit/` | Admin or owning Manager edit |
| `/projects/<id>/` | Scoped project Overview |
| `/projects/<id>/team/` | Scoped Team, read-only for Employees |
| `/projects/<id>/report/` | Scoped Report; Employees see labelled Own work |
| `/projects/<id>/team/add/` | Admin or owning Manager active Employee picker |
| `/projects/<id>/team/<employee_id>/remove/` | Confirmation then POST removal; unfinished-task guard |

Create/edit forms share templates and existing services. Only Admin sees a project
Manager selector; Manager ownership comes from the actor. Role changes require an
explicit checkbox and the existing reassignment guards. Blank password reset keeps
the current password. Deactivation preserves all history. Lists paginate 25 records
in ID order; searches operate within authorized scope. All mutations use POST/CSRF.

The desktop shell uses bundled IBM Plex Sans, a 48px header, 240px sidebar, neutral
surfaces and square controls. Native date controls follow browser locale. Task titles on Overview link to task details. Project Tasks is reachable from every
project section; Employees have My tasks navigation. All required account, project,
team, task and time workflows run outside Django Admin.

Install Chromium once, then run the isolated UI checks (no development server needed):

```bash
uv run playwright install chromium
uv run pytest tests/test_workspace_html.py tests/test_workspace_browser.py -q
```

The browser fixture serves Django/static files on an ephemeral local port and seeds
only the PostgreSQL test database. It creates/edits/deactivates fixture accounts and
projects, preserving development data and demo credentials. It captures screenshots
in `docs/evidence/workspace/`. Browser checks also run with `uv run pytest` and require
Chromium to be installed. Linux hosts may need `uv run playwright install --with-deps chromium`.
See [Phase 4A verification](docs/workspace-ui-verification.md) for actual results,
Paper comparisons, keyboard/reflow scope and remaining work. These are automated
checks; the assignment's human manual cases remain pending.


## Task and time desktop workflow (Phase 4B)

| Route | Screen/action and access |
| --- | --- |
| `/projects/<id>/tasks/` | Scoped team task summaries; status/assignee filters |
| `/projects/<id>/tasks/create/` | Admin/owning Manager create and assign a TODO task |
| `/my-tasks/` | Employee current assignments; status/project filters, default unfinished |
| `/tasks/<id>/` | Scoped task details, progress, readable time history |
| `/tasks/<id>/edit/` | Admin/owning Manager edit/reassign unfinished tasks |
| `/tasks/<id>/start/` | POST start; assigned Employee or Admin/owning Manager |
| `/tasks/<id>/complete/` | GET confirmation, POST completion; same actors |
| `/tasks/<id>/delete/` | GET confirmation, POST safe unfinished deletion; Admin/owning Manager |
| `/tasks/<id>/time/add/` | Inline or full-page Log time; assigned Employee on IN_PROGRESS task |
| `/time-entries/<id>/edit/` | Own time edit while still assigned and IN_PROGRESS |
| `/time-entries/<id>/delete/` | GET confirmation, POST own time deletion under the same rule |
| `/tasks/<id>/correction/` | Explicit Admin completed-task correction; status retained |
| `/time-entries/<id>/correction/` | Explicit Admin historical/current time correction; identity retained |

Every mutation calls the existing services and requires POST with CSRF. Task project
and time contributor/task identity are fixed. Task assignment options are active project
Employees; edit forms allow blank to keep an existing historical/inactive assignee.
Filters include current members and historical assignees, without foreign users.
Lists use 25-row ID ordering and retain filters when paging. Invalid filters render 400;
ordinary HTML validation/save errors retain values with 200; stale/forbidden service
writes retain values with 403. Foreign/missing objects return 404; unsupported methods
return 405. Repeated current status is a no-op, including repeated completion POST.

The HTML time form accepts whole Hours and additional Minutes (0–59), with a total
from 1 minute to 24 hours. For example, 3 hours and 0 minutes saves 180 minutes.
Create, edit and Admin correction share this form; existing entries split into hours
and minutes for editing. PostgreSQL and the REST API still use whole minutes 1–1440
and a nonfuture date. An Employee sees only their own
detailed time/notes and original contributions; Admin/owning Manager can read project
history. Managers cannot edit time. Reassignment/completion immediately blocks ordinary
time writes; completed work exposes read-only guidance and explicit Admin corrections.
Completion asks users to record remaining time first. Delete time requires confirmation;
tasks with recorded history cannot be deleted. Admin cannot reopen/delete completed tasks
or invent/delete historical time through correction forms.

```bash
uv run pytest tests/test_task_html.py tests/test_task_browser.py -q
```

These checks use isolated PostgreSQL fixtures and Chromium. Screenshots are in
`docs/evidence/tasks/`; [Phase 4B verification](docs/task-ui-verification.md) records
actual results and Paper differences. [Manual cases](docs/manual-test-cases.csv) are
prepared with NOT RUN status for human execution; automated checks do not mark them PASS.

# Assignment review and implementation plan

Reviewed: 7 October 2026. The assessment below records the original scaffold.
Progress update: authentication and the project data foundation are implemented and verified on PostgreSQL; see `auth-foundation-verification.md` and `project-data-verification.md`. Phase 2 shared actor operations and scoped reads are implemented; see `business-rules.md`. Phase 3 adds resource REST APIs, scoped basic reports and SQL comparison; application screens and executed manual evidence remain pending. Phase 4A adds the desktop shell, dashboards, account and project/team/report screens; see `workspace-ui-verification.md`. Phase 4B completes task/time desktop workflows; see `task-ui-verification.md`. Human manual evidence and clean-checkout rehearsal remain pending. The original scaffold assessment below is historical.

## Assignment source and deadline

Reviewed both pages of the supplied `Gmail - Technical Assignment – Project & Resource Management System.pdf`, including rendered pages. The email is dated 6 October 2026, 6:36 PM and requires completion within three days of receipt. Plan to finish before 9 October; a literal 72-hour interpretation would be 9 October at 6:36 PM in the email's displayed timezone. The email does not state a separate submission hour or timezone.

The company requires Django, DRF, PostgreSQL or MySQL, HTML/CSS/JavaScript, three roles, the listed management/workflow/report features, business-rule validation, at least 20 manual cases, positive/negative workflow/API/security cases, SQL reports, and seven submission deliverables. The attachment is the requirements source; this review request authorizes inspection and planning, not submission or deployment.

PostgreSQL, uv, Django templates, IBM-inspired styling, manual minutes, account deactivation, 30 manual cases, strict forward transitions, and detailed Admin correction semantics are repository choices. Preserve that distinction in documentation.

## Current repository assessment

| Area | Observed state | Required next work |
| --- | --- | --- |
| Dependency setup | `pyproject.toml` and `uv.lock` committed; Django, DRF, psycopg and test tooling declared | Install locked environment and verify commands |
| Django scaffold | `config/`, `accounts/`, `projects/` exist | Register apps and configure actual application |
| Configuration | SQLite, literal generated secret, DEBUG=True, empty hosts; environment example exists but is unused | Environment-backed PostgreSQL, secret/debug/hosts, template/static configuration |
| Users and data | Both app model files are placeholders; no application migrations | Custom role-aware User before initial migrations; Project, Membership, Task, TimeEntry |
| UI/API | Placeholder views; root URLs expose only Django Admin; no templates/static/API modules | Session login and complete template/API workflows |
| Permissions and rules | No application implementation | Shared services, scoped querysets, field permissions, validation, transactions |
| Tests | Generated placeholder test files; no pytest project configuration | Fixtures and meaningful backend/API tests |
| Submission evidence | No README, schema/API docs, manual cases, SQL reports or limitations document | Create, execute, and maintain deliverables |
| Design/instructions | Root `AGENTS.md`, `design.md`, reference `docs/DESIGN-ibm.md`, external RTK instructions reviewed | Follow adapted application design and backend policies |

No required feature R01-R10 is implemented in the inspected scaffold. Existing specifications are useful but do not prove functioning behavior.

### Checks actually attempted

- Git was clean before this plan was added; inspected commit: `463d8cc`.
- `uv run --locked --no-sync python manage.py check` initially encountered a sandbox restriction on the default uv cache. Retrying with a temporary cache created an ignored `.venv`, then failed because Django was not installed. Dependencies were not synchronized during this review; no successful Django check is claimed.
- `pg_isready -h localhost -p 5432` returned no response. PostgreSQL client tools exist; server/database availability and test database privileges remain unverified.
- No application tests, manual cases, browser flows, migrations, SQL reports or clean setup were executed.

## Instruction and design review

`AGENTS.md` covers the assignment and adds useful explicit product policies, security checks, evidence standards and a narrow scope. `design.md` adapts a marketing reference into a feasible template-based application: compact tables, neutral surfaces, blue actions, square controls, persistent labels and clear role/status states. Use it as the UI contract. Do not implement the reference's marketing sections or its suggested lint command automatically.

Resolve these details before implementing the affected feature:

1. Employee report scope: `design.md` says employees see their own work summary, while project/team task summaries remain visible within their membership projects. Define employee reports as own assigned-task counts and own logged minutes, label that scope, and keep other employees' detailed time notes private. Admin/Manager project reports show permitted project totals and contributor hours. Document the choice consistently.
2. Account role changes: define a guarded policy for accounts that own projects, hold memberships, or have unfinished assignments. Prefer rejecting changes that invalidate those relationships, with instructions to reassign work first.
3. Explicit Admin corrections: define the authorized operation and editable fields. Preserve completed status; normal users must never enter this bypass.
4. Reference filename: `AGENTS.md` mentions an attachment with `(2)` in its name; this review used the supplied filename without that suffix. Use the actual reviewed attachment name in new documentation.

## Ordered implementation plan

### 1. Foundation and requirement map — 7 October

- Map R01-R10 to model/service, API, UI, automated cases and manual cases in `docs/requirements.md`.
- Run `uv sync --locked`; configure environment loading without exposing secrets.
- Configure PostgreSQL and a dedicated test database role with creation privileges. Keep resets explicit.
- Register `accounts`, `projects`, DRF; configure templates/static and default authenticated API access.
- Create custom User with Admin/Manager/Employee roles and `AUTH_USER_MODEL` before initial migrations.
- Implement entities, protected history, membership uniqueness, valid statuses, project date ordering and bounded positive minutes.
- Create migrations and idempotent `seed_demo` for Admin, two Managers, multiple Employees and unassigned/empty/partial/completed examples.
- Add a minimal README immediately so setup stays reproducible.

Acceptance: PostgreSQL migrations and seed command run; seed is repeatable; Django check and migration drift checks pass.

### 2. Shared backend rules and first complete journey — 7 October

- Build scoped querysets and small reusable mutation services used by both HTML and DRF.
- Implement project creation, membership addition, task assignment, start, time logging, completion and report calculation.
- Whitelist writable fields, derive ownership from the authenticated user, and reject forged role/manager/project/time-owner fields.
- Validate create, PUT and PATCH consistently; support same-status no-op, prohibit skipping/reopening, and lock completed records for normal users.
- Serialize competing operations with a documented lock order: project, task, then affected membership/time rows. Recheck permission/membership/status after locking.
- Test the first journey and failures with two Managers and unrelated Employees before broadening UI work.

Acceptance: permitted workflow succeeds through the API on PostgreSQL; foreign access, nonmember assignment, reversed dates and completed-task edits fail; report totals agree with persisted entries.

### 3. Complete APIs and template screens — 8 October

- Complete Admin account create/list/edit/deactivation, project edit, membership removal guards, task detail/reassignment and own time-entry edit/delete behavior.
- Implement explicit Admin corrections and document protected deletion behavior.
- Add paginated `/api/` resources, minimal manager employee picker, scoped filters/reports and documented response codes.
- Implement CSRF-protected session login, POST logout, inactive-account rejection and restricted Django Admin access.
- Build shared header/sidebar, fields, tables and status components using `design.md` tokens; bundle IBM Plex Sans with license.
- Build Login, role-specific Overview, Employees, Projects/create/edit, Project details with team/tasks/report, My tasks and Task details/time forms.
- Preserve values after validation failures; show saving/failure/empty/read-only states and stale-state rejection messages.

Acceptance: Manager and Employee complete the full journey through reachable screens; Admin manages accounts; no essential operation requires Django Admin.

### 4. Testing, SQL and evidence — start 7 October; finish 8 October

- Configure pytest-django with PostgreSQL and add focused service/model/API tests alongside each feature.
- Cover date equality/reversal; required/invalid PATCH fields; duplicate/inactive/nonmember assignment; foreign manager/employee writes; list/detail/filter/report isolation; forged fields; transitions; completion/time/deletion locks; time ownership and integer boundaries; historical attribution; CSRF; inactive sessions; and meaningful concurrent mutations.
- Draft 30 manual cases with all prescribed columns and NOT RUN status. Execute them against the application, capture actual outcomes/evidence, record defects and retest fixes. At least 20 cases are required by the company.
- Create `sql/project_reports.sql`: project task/status counts, completion, project hours and employee/project hours. Aggregate tasks and time separately, include zero-work projects and historical contributors, and compare results with application reports.
- Inspect keyboard operation, focus/contrast, 200% zoom and 1440/1024/768/390/320px layouts. Add a few browser journeys if feasible without displacing required evidence.

Acceptance: executed PostgreSQL tests and manual results exist; SQL and app metrics agree; negative security checks are evidenced; defects are resolved or disclosed.

### 5. Submission rehearsal and explanation — 9 October, with buffer

- Finish README, `docs/schema.md`, `docs/api.md`, `docs/manual-test-cases.csv`, referenced evidence, defect notes and `docs/known-limitations.md`.
- From a clean checkout, rehearse locked sync, environment/database setup, migrate, seed, run and tests. Commit migrations and all required source/documentation files.
- Re-run `manage.py check`, `makemigrations --check --dry-run` and the appropriate PostgreSQL test suite after final fixes.
- Prepare a concise demo: Manager creates project/team/task; Employee starts/logs/completes; forbidden edit fails; report and SQL agree.
- Prepare explanations of relationships, permissions, completion locking, transaction handling, report aggregation and one observed bug/fix.

Acceptance: all seven submission deliverables are present, setup is reproduced, actual tested scope and limitations are stated honestly. Sending, publishing or deployment requires separate user authorization.

## Scope and priority

Prioritize working assignment features, backend enforcement, required tests and reproducible documentation. Keep the first complete journey ahead of cosmetic polishing. Exclude boards, timers, dark mode, charts, notifications, chat, billing, AI, React migration and unrelated infrastructure. Optional browser automation and visual refinements follow required evidence, never replace it.

The schedule is a target, not a completion guarantee. Environment setup is the first dependency; postpone optional work if infrastructure or rule defects consume the buffer.

# AGENTS.md — Project & Resource Management System

## Purpose and scope

Build a reviewable Django development and testing assignment for Piiritu Innovations. Managers create projects, assign employees and track tasks. Deliver working features, enforced permissions, executed testing evidence and reproducible setup.

This file belongs at the repository root and governs development throughout the repository unless a more specific AGENTS.md applies. Read `design.md` before UI work. The supplied `DESIGN-ibm.md` is visual reference material; the adapted `design.md` defines our application UI.

Source of requirements: the candidate's email dated 6 October 2026, attached as “Gmail - Technical Assignment – Project & Resource Management System(2).pdf”. The attachment requires completion within three days of receipt. Do not add scope that jeopardizes required features, testing or documentation.

Precedence: explicit user instructions and assignment requirements > documented product policies below > implementation preferences. If a requirement is ambiguous, document a reasonable assumption and proceed; seek clarification only when the choice materially changes the assignment. Do not describe project choices as company requirements.

## Required stack and features

The assignment requires Django, Django REST Framework, PostgreSQL or MySQL, and HTML/CSS/JavaScript. Our selected database is PostgreSQL. Use Django templates, same-origin JavaScript and DRF APIs. Use `uv` for dependencies and commit `pyproject.toml` and `uv.lock`. Resolve compatible supported versions when initializing, then lock them. Do not substitute SQLite for final database verification.

Roles: Admin, Project Manager, Employee.

| ID | Assignment requirement | Minimum implementation |
| --- | --- | --- |
| R01 | Employee management | Account creation, listing, editing and safe deactivation |
| R02 | Project management | Project creation, listing, details and editing |
| R03 | Employee/project assignment | Project membership management |
| R04 | Task management and assignment | Project tasks assigned only to project members |
| R05 | Task status | TODO → IN_PROGRESS → COMPLETED |
| R06 | Project start/end dates | Validated on create and update |
| R07 | Time tracking | Persistent task work-duration entries |
| R08 | Basic project reports | Task breakdown, completion and recorded hours |
| R09 | REST APIs | Documented endpoints for required operations |
| R10 | Role-based access | Backend enforcement on every entry point |

Deactivation, manual duration entry and exact report metrics are our chosen implementations of the broader requirements.

## Mandatory business rules

1. Employees can only work on projects to which they are assigned.
2. Tasks can only be assigned to project members.
3. Employees can update their assigned tasks; unrelated tasks must reject modification.
4. Project Managers can manage their projects; another manager's project must reject modification.
5. Completed tasks cannot be modified by normal users.
6. Project end date cannot precede start date; equal dates are permitted.
7. Validate required fields and invalid values on both creation and partial/full updates.

Enforce these rules in backend operations used by both UI and API. Hidden buttons, filtered dropdowns and JavaScript checks are not authorization. Never assume model `clean()` runs automatically on every save. Use explicit validation and database constraints where suitable.

## Documented project policies

These defaults resolve omissions in the assignment and align with `design.md`. Preserve them consistently across UI, API and tests; document any deliberate revision.

- Admin manages all accounts and projects. Managers create projects owned by themselves. Only Admin can choose or change a project's manager.
- Managers control team membership, task details and task assignment within their projects.
- Employees can view membership projects and team task summaries; their edit access is limited to their own task status and own time entries. Foreign projects are unavailable. Other employees' detailed time notes are not exposed.
- Treat Managers and Employees as normal users. Completed tasks and their time entries are read-only to them, including delete/reassignment requests.
- Admin may correct completed-task details or time entries through an explicit authorized operation; this does not silently reopen a task.
- Normal workflow moves forward one step at a time, with no skipping or reopening. Repeating the current status may be an idempotent no-op; document this behaviour. New tasks begin at TODO.
- Manual time entries use a work date, positive whole minutes and an optional note. Employees log only against their own assigned IN_PROGRESS tasks. No future dates; maximum 1440 minutes per entry. This is a per-entry validation limit, not an overlap detector or daily capacity rule.
- Deactivate accounts instead of deleting work history. New assignments require active Employee accounts and valid membership. Inactive users cannot use existing authenticated sessions to perform work.
- Block membership removal while unfinished tasks remain assigned. Preserve attribution of historical time when tasks are reassigned or members removed.
- Protect records with dependent work/time history from destructive deletion; document available deletion behaviour. Never cascade-delete evidence casually.
- A project with zero tasks displays “No tasks yet” and a report completion value of 0; other percentages use completed task count / total task count.

## Architecture and data

Start with a small conventional structure; do not add layers solely for abstraction:

| Location | Responsibility |
| --- | --- |
| `config/` | Settings, root URLs and deployment entry points |
| `accounts/` | User role, authentication and employee operations |
| `projects/` | Projects, membership, tasks, time entries, permissions and reports |
| `templates/` | Shared layout, components and feature pages |
| `static/` | CSS tokens, component styles, minimal JavaScript and licensed fonts |
| `tests/` | Model, business-rule, API and browser tests |
| `docs/` | Schema, API docs, executed manual cases and limitations |
| `sql/` | Read-only report queries |

Core entities: User, Project, ProjectMembership, Task, TimeEntry. Establish a custom user model and AUTH_USER_MODEL before initial migrations. Use Django password hashing; never store plaintext passwords.

Use foreign keys and a unique (project, employee) membership constraint. Constrain valid task statuses, project date ordering and positive bounded minutes. Validate cross-table membership explicitly. Add indexes for frequently filtered foreign keys/status as justified by actual queries.

Place shared mutation rules in a small service module or equivalent reusable operations. Call it from DRF and HTML views; avoid divergent validators. Use transactions for related writes. Serialize competing mutations affecting task completion, time logging, assignment and membership as needed using row locks and fresh state checks. Define a consistent lock order and test meaningful competing operations rather than relying only on UI state.

## Authentication, API and authorization

- Use Django session authentication for the same-origin app and DRF; enforce CSRF on login and state-changing requests. Logout uses POST.
- Require authentication by default. Restrict list querysets before pagination, filtering or aggregation; check object and field permissions on writes.
- Clients cannot set their role, forge the logged-time employee, appoint themselves to foreign projects, move a task to another project or mutate protected fields through bulk/partial updates.
- Whitelist writable fields per action/role. Never trust hidden inputs for ownership. Apply the same rules to Django Admin if exposed; keep normal users out of administrative bypass paths.
- Use stable `/api/` resource routes, meaningful validation errors and documented response codes. Validation failures are 400; authenticated forbidden actions are 403; unavailable/out-of-scope objects may be 404. With DRF SessionAuthentication, unauthenticated rejection can be 403; document actual behaviour rather than promising 401 universally.
- Paginate list APIs. Scope report endpoints and employee picker options; managers receive only the minimal employee data necessary for membership selection.
- Use ORM queries by default and parameterized SQL when executing raw queries. Never interpolate user input into SQL.
- Keep SECRET_KEY and database credentials in environment variables, provide `.env.example` placeholders and ignore `.env`. Log useful errors without passwords, cookies or sensitive payloads.

## UI and UX contract

Follow `design.md`: IBM Plex Sans, restrained primary blue, neutral surfaces, square components, compact readable tables, shared sidebar/header and role-specific actions. Implement the complete authorized workflow outside Django Admin.

Required screens: Login, Overview, Employees (Admin), Projects, Project details with team/tasks/report, My tasks and Task details with time logging. Create/edit forms must be reachable.

Use persistent labels, inline errors, clear status text, empty/loading/saving/failure states and a completed-task read-only explanation. Preserve input after failed saves. Refresh after mutations and explain stale-state rejections. Do not imply unimplemented capabilities.

Check keyboard navigation, visible focus, contrast, accessible tables, responsive forms and narrow-width table scrolling. Inspect 1440, 1024, 768, 390 and 320px layouts. A Stitch design is a visual reference, not proof that backend behaviour exists.

## Development sequence and working habits

1. Map every requirement to model/API/UI/tests; document assumptions.
2. Set up project, PostgreSQL, roles, migrations and deterministic demo accounts.
3. Build one complete journey: project → membership → task → start → log time → complete → report.
4. Complete remaining account, project and permission behaviour.
5. Test, fix defects, verify reports, finish docs and rehearse a clean setup.

Read existing code before changing it. Prefer small understandable functions and meaningful names. Avoid microservices, React migration, background workers, live timers, chat, billing, AI features or ornamental features. Preserve user work. Do not publish, email, submit or deploy without user authorization. Preparing code and documentation is authorized by the development task.

## Commands and environment

Once configured, the repository must support these commands from its root. Do not claim a command passed before running it. If the structure differs, update this section and README together.

```bash
uv sync --locked
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest
```

Implement `seed_demo` as an idempotent management command for explicit development/test use; do not seed demo passwords into production automatically. Configure pytest-django and PostgreSQL test database privileges. Keep destructive resets opt-in.
If browser automation is included, document its installation and invocation exactly in README. If a check is blocked by missing infrastructure, record the blocker and unverified scope; do not silently replace PostgreSQL.

## Testing and evidence

The company requires at least 20 manual cases, positive and negative scenarios, project/task workflow tests, API cases, permission/security cases and SQL report queries. Target 30 manual cases while satisfying every category.

Manual case columns: Test ID, Requirement ID, Scenario, Preconditions, Steps, Test data, Expected result, Actual result, Status, Priority, Evidence. Default status is NOT RUN. Record PASS/FAIL only after execution; capture actual outcomes and useful evidence. Record defects with reproduction, expected/actual results and severity; retest fixes.

Automate high-value backend checks with pytest/pytest-django:
- Date equality/reversal, missing values and invalid statuses on create and PATCH.
- Assignment outside membership, inactive assignees and duplicate membership.
- Employee editing another task, manager editing another project and forged ownership/role fields.
- Data isolation on list/detail/filter/report endpoints, not only update endpoints.
- Valid workflow, invalid transitions, completion lock including delete/time edits, and intentional Admin correction.
- Time ownership, integer/boundary validation, reassignment attribution and accurate aggregation.
- Real CSRF enforcement, inactive-account access and transaction-sensitive rules where applicable.

Use fixtures with Admin, two Managers, multiple Employees, at least two separately owned projects and an unassigned employee. Include zero-task, partially complete and completed-task states. Use a small number of Playwright journeys if feasible. Backend tests do not replace the required manual cases.

SQL queries must execute on the selected PostgreSQL schema and cover per-project task/status counts, completion percentage, project hours and employee/project hours. Include projects with no tasks or time. Aggregate tasks and time separately where needed to avoid join multiplication; preserve historical contributors. Compare results with app reports on seeded data. Avoid unsupported utilization, budget or productivity claims.

## Submission and definition of done

| Required submission | Repository deliverable |
| --- | --- |
| Source code / Git repository | App, migrations, dependency manifest and lockfile |
| Database/schema information | `docs/schema.md`, relationships and constraints |
| README with setup instructions | `README.md`: environment, PostgreSQL, migrations, seed accounts, run/test commands |
| API documentation | `docs/api.md`: routes, authentication/CSRF, permissions, examples and errors |
| Manual test cases | `docs/manual-test-cases.csv`, executed results and referenced evidence |
| SQL queries | `sql/project_reports.sql` with report scope comments |
| Known limitations | `docs/known-limitations.md`, including assumptions and unverified work |

Before reporting completion, run appropriate checks and tests on PostgreSQL; confirm migrations are committed; execute required manual cases; verify SQL/report agreement; inspect key UI flows; and reproduce setup from a clean checkout. Keep tests targeted and meaningful rather than mirroring implementation.

Final status must state what works, what was actually tested and what remains limited. The candidate must be able to explain the data relationships, role enforcement, completion lock, report SQL and a representative bug/fix. Never invent results, hide blockers or call a prototype a completed assignment.

# Phase 3 — REST and reports verification

Executed: 7 October 2026. Starting commit: `c903f50` (Phase 2). Checkout was clean.
Scope: conventional DRF adapters, scoped basic reports, read-only SQL and HTTP tests.

## Implementation and preservation

- Added account, project, membership, active Employee picker, task, time-entry,
  explicit Admin correction, project report and Overview endpoints. Exact routes,
  fields and response shapes are in `api.md`.
- All mutations call the unchanged shared services. Existing selectors scope resource
  reads; one additive selector authorizes minimal employee picker options. Account
  lists use a small Admin-only selector. No new locking architecture was introduced.
- Serializers parse transport types and reject unknown fields. Role/action/model
  rules remain in services/models. PUT intentionally behaves as a partial update.
- Reports aggregate tasks/time separately, use original contributor IDs and label
  Employee work scope. Decimal half-up hours/percentage rounding matches SQL ROUND.
- Diff inspection confirms existing models, applied migrations, shared services,
  authentication flows, seed implementation and all 162 existing tests unchanged.
  Settings add only the error adapter; root URLs add resource routes.
- No UI, public signup, JWT, background jobs, export system, migration rewrite,
  development database reset, push or deployment.

## Checks actually executed

All commands used the existing uv environment with `--cache-dir .cache/uv`.
PostgreSQL required local sandbox access; no SQLite substitute was used.

| Check | Actual result |
| --- | --- |
| Focused HTTP/SQL suite after 404 correction | 59 passed in 8.97 seconds |
| Full suite after all additions and fixes | 224 passed in 38.23 seconds |
| Existing suite within that run | All 162 passed, including 31 authentication tests |
| New HTTP/report/SQL tests within that run | All 62 passed |
| `python manage.py check` | No issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `ruff check accounts config projects tests scripts` | Passed |
| `ruff format --check accounts config projects tests scripts` | 48 files already formatted |
| `git diff --check` | Passed |

HTTP tests execute session-backed requests, not forced DRF authentication. The CSRF
case signs in through the real HTML login with CSRF checks enabled, confirms a PATCH
without its header is denied (403), then confirms the same mutation with the rotated
CSRF cookie header succeeds (200).

Coverage includes the Manager → project/member/task → Employee start/time/complete
journey; Admin stored-role access without staff/superuser; foreign Manager/unrelated
Employee list/detail/filter/report isolation; private time notes; protected field
forgery; boolean/fraction/string minute rejection; partial PUT/PATCH; bad dates/status
and missing input; account role/password guards; completed mutation locks and explicit
corrections; protected deletion errors; pagination; employee picker scope; inactive and
initial-password session rejection; ownership changes and deactivation access revocation.

Reports are tested with multiple entries per task, zero-task projects, multiple
contributors, task reassignment, membership removal and an inactive historical
contributor. Employee Overview/project reports exclude other employees' metrics/notes.

## SQL versus application comparison

Executed both statements in `sql/project_reports.sql` using a read-only repeatable-read
PostgreSQL transaction via `scripts/verify_project_reports.py`, against the existing
development seed. No reseeding or writes were performed. Both project aggregates and
all original contributor aggregates matched Admin application reports.

| Existing project | Tasks | Completed | Recorded minutes |
| --- | --- | --- | --- |
| Client Website Redesign | 6 | 2 | 720 |
| Employee Onboarding Portal | 5 | 2 | 720 |
| Internal Knowledge Base | 0 | 0 | 0 |
| Operations Handbook | 1 | 0 | 0 |

Actual script result: 4 projects compared, 4 project/contributor aggregates compared,
`MATCH`. Website is 33.33% complete / 12 hours; Onboarding 40% / 12 hours; the two
zero-time projects have zero hours. Empty projects retain zero-valued SQL report rows.
Automated SQL comparisons also matched a fresh seed and a separate fixture with
multiple time entries, reassignment, membership removal and a zero-task project.

Reproduce without changing records:

```bash
uv run python manage.py shell -c 'from scripts.verify_project_reports import verify; print(verify())'
```

## Defects found and corrected

- Initial DRF missing-object errors named individual model classes while service
  errors used another message. HTTP assertions caught this. The error adapter now
  maps both Http404 and ObjectDoesNotExist to the same unavailable response; retests passed.
- The first SQL comparison parser split a semicolon inside a SQL comment into an
  empty statement. Removed that comment delimiter; both queries then executed/matched.
- A late ownership/deactivation test initially lacked its Project import. Corrected
  the test; the final full suite passed. Earlier failing runs are not claimed as passes.

## Remaining work and blockers

No infrastructure blocker remains for this phase. The application pages still show
the authentication foundation, not the Paper workspace. Next: shared desktop layout,
role-specific Overview, Employees, Projects/detail/team/report, My tasks and task/time
forms using these APIs with CSRF, accessible controls and error states. Required manual
case execution, browser checks and clean-checkout submission rehearsal remain pending.
Automated HTTP/SQL tests do not replace the assignment's manual evidence.

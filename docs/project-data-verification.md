# Project data foundations — executed verification

Date: 7 October 2026. Scope: project data models, additive migration and development seed.

## Starting state and preservation

- Fetched current `origin/main`: `c407ee2` (merged authentication foundation).
- Created local `codex/project-data-foundations` from that main commit.
- Inspected required repository/design/setup/schema/plan/Paper handoff documents and code.
- Inspected PostgreSQL `prms_b532` before changes: seven User rows; accounts initial
  migration and standard Django migrations applied; no `projects_` tables.
- Inspected `migrate --plan`: only `projects.0001_initial`, adding the four tables,
  row constraints and task indexes. Applied it without reversing/deleting migrations
  or resetting records. `showmigrations` confirms projects and accounts initial migrations applied.
- Diff against main confirms custom User, accounts initial migration, authentication
  views/forms/middleware, configuration, templates and static assets are unchanged.
  Only the existing seed command was extended within the accounts package.
- No resource pages/APIs/Admin registrations, push, merge, deployment or database reset.

## Executed checks

Commands used the locked uv environment and writable `.cache/uv` cache. PostgreSQL
connections required sandbox access; no SQLite substitution or infrastructure blocker remained.

| Check | Actual result |
| --- | --- |
| python manage.py migrate --plan | Only the additive project migration pending |
| python manage.py migrate | projects.0001_initial applied successfully |
| python manage.py showmigrations projects accounts | Both initial migrations applied |
| python manage.py check | No issues |
| python manage.py makemigrations --check --dry-run | No changes detected; PostgreSQL history checked |
| pytest -q | 111 passed in 25.12 seconds on a separate PostgreSQL test database |
| Existing authentication tests | All 31 passed within the final suite |
| New model/seed/concurrency tests | All 80 passed within the final suite |
| ruff check accounts config projects/models.py projects/demo.py projects/migrations tests scripts | Passed |
| ruff format --check on the same paths | 29 files already formatted |
| git diff --check | Passed |

Tests cover required fields, whitespace/length/date validation, equal dates, role/activity
selection, membership uniqueness, nonmember/inactive assignment, valid/default/invalid
statuses and forward/no-op transitions, immutable task project, effective partial updates,
minute type/bounds, future/invalid dates, contributor/assignment/membership checks,
original attribution after reassignment/removal/deactivation, immutable time identities,
protected instance/queryset deletion, database constraints and foreign keys.

Two competing-operation tests use separate PostgreSQL connections and verify the second
operation actually waits on a database lock. Assignment-first rejects subsequent membership
removal; removal-first rejects subsequent assignment. These are data-layer serialization
checks, not actor/API permission tests.

## Development database seed verification

Ran `seed_demo` twice in the actual development database. Compared all pre-existing
User field values (including password hashes) before and after first seeding: unchanged.
Compared every row in all five entity tables before/after the second seed: unchanged.
No credentials or password hashes were printed.

| Entity | Actual count |
| --- | --- |
| User | 7 |
| Project | 4 |
| ProjectMembership | 5 |
| Task | 12 |
| TimeEntry | 7 |

Actual project totals: Website 6 tasks / 2 completed / 720 minutes; Onboarding 5 tasks /
2 completed / 720 minutes; Knowledge Base 0 tasks / 0 minutes; separately owned Operations
Handbook 1 TODO task / 0 minutes. Website contributor sums were inspected: Asha 420 minutes,
Ravi 300 minutes. Automated seed checks additionally verify Neha's three-project totals
(7 unfinished, 4 completed, 1440 minutes) and Asha's own status counts (2 each) / 780 minutes.

Preservation tests cover edited names/descriptions/task titles, time durations/notes,
password/name/activity changes, deleted child tasks, and unrelated user work with matching
display names. A conflicting existing account causes an atomic failure instead of an
account repair/reset. Demo totals are a fresh-fixture contract, not a restoration target
after user changes.

## Remaining scope

Actor-aware mutation/permission services, coordinated account role changes, scoped reads,
normal-user completed-record locks and explicit Admin corrections must precede resource
pages/APIs. Report SQL/application reports, required manual evidence and final clean-checkout
rehearsal remain for later phases. The model layer does not know the logged-in actor;
bulk/raw writes bypass its cross-table validation. See `schema.md` and `known-limitations.md`.

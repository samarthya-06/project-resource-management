# Phase 2 — shared business operations

The application boundary is `projects/services.py`, `projects/selectors.py` and
`accounts/services.py`. Future HTML views and DRF must call these functions rather
than save models directly. No resource endpoint or screen is introduced here.
Models, migrations, authentication, demo seeding and their existing tests are preserved.

## Authorization and input contract

Each public operation accepts the authenticated actor and target primary keys, plus
explicit keyword fields. Actor role, activity and initial-password state are reread
from PostgreSQL; a stale in-memory user cannot keep privileges after deactivation,
role change or password reset. Anonymous, inactive and initial-password actors are denied.
IDs use `manager_id`, `assignee_id` and `employee_id`, not arbitrary model objects.
Unknown/protected fields raise Django ValidationError, permissions raise
PermissionDenied, and out-of-scope details raise model DoesNotExist. Future adapters
must map all ObjectDoesNotExist exceptions to the same unavailable/404 response.
They must never serialize arbitrary model relations or private time notes.

- Admin creates/manages all projects and chooses an active Manager. A Manager's new
  project derives its owner from the actor; specifying even their own manager ID is
  rejected. Only Admin changes ownership. Employees cannot manage projects.
- Admin/owning Manager adds active Employee members, removes members, creates and
  edits tasks, assigns project members and moves task status forward. Existing
  model validation rejects duplicates, nonmembers, inactive assignments and removal
  while unfinished tasks remain assigned. Inactive members can be removed after
  reassignment/completion; cleanup must not require reactivating them.
- Employees update only their assigned task's status within a membership project.
  TODO → IN_PROGRESS → COMPLETED is mandatory. Repeating the current status is a
  no-op, including COMPLETED; it grants no permission to change any other field.
- Completed tasks reject ordinary edits/reassignment/deletion. Admin uses
  `correct_completed_task` for title, description or valid member reassignment;
  COMPLETED is retained. Completed deletion is deliberately unavailable even to
  Admin; corrections retain history. Other deletions reuse PROTECT constraints.
- Employees create/update/delete only their own time while the task is assigned to
  them, in their membership project and IN_PROGRESS. Creation derives the contributor
  from the actor. Task/contributor IDs cannot be edited. Reassignment immediately
  prevents the old contributor from editing; the new assignee cannot edit that history.
- Managers never mutate employee time. Admin uses `correct_time_entry` to edit date,
  integer minutes or note, including historical/completed entries. Attribution and
  task status are retained. Admin cannot invent contributions or delete historical
  entries via these operations. Whole-minute, 1–1440 and nonfuture date checks reuse
  the models. No daily capacity or overlap rule is added.

## Scoped reads

`projects_for` / `project_for`: Admin all, Manager owned, Employee membership projects.
`tasks_for` / `task_for` follow that scope. `task_summaries_for` returns only ID,
project ID, title, assignee ID and status for team summaries. Time selectors scope
projects first, then restrict Employees to their own entries/notes. Admin and the
owning Manager can read project time details. Former members lose access even to
old contributions in that project; history remains available to its Manager/Admin.
Querysets are for immediate request use, not caching across account/permission changes.

## Accounts and administrative surface

Only Admin may create/edit/deactivate accounts. Writable profile fields are username,
email, first/last name and role; an optional password reset validates Django password
rules, hashes the password and sets must_change_password. Account creation requires
an initial password and the same gate. Staff/superuser/groups/permissions and the gate
are never application-writable. Accounts are created active; reactivation is outside
this phase's operations. Deactivation preserves all relationships and contributions.

A role change requires reassignment of owned projects and unfinished tasks, and
removal of memberships first. Completed assignments and original time attribution
may remain after the role changes. Errors explain the prerequisite. Existing
privileged Django Admin accounts retain the model's Admin-role constraint.
Django Admin keeps its existing superuser-only access; existing roles are read-only
there so its model form cannot bypass the application role-change guard. Provisioning
and authentication otherwise retain their existing behavior.

## Transactions and locks

Each mutation is atomic and uses ordinary validated saves; no bulk updates.
Operations lock the actor and any chosen manager/assignee/member in ascending User ID
order, then the existing containing Project lock, then model row locks from the
unchanged ValidatedModel. They reread task status and authorization after obtaining
those locks. Project locking serializes completion, time edits and assignment/removal.
Account edits lock the actor and target User in the same order. This additional user
lock closes a specific race: role/activity changes checking relationships while a
new ownership/membership/assignment is being created. A PostgreSQL test confirms
membership addition waits for deactivation, then rejects the inactive account.
These guarantees apply to shared operations; trusted model-only seed/bootstrap work
must not run concurrently as an alternative application mutation path.

## Remaining work

Wire these operations into authenticated, CSRF-protected HTML and DRF actions with
field parsing and consistent errors. Add account listings/employee pickers, reports,
SQL, API tests, Paper screens and required executed manual evidence. This phase's
function tests do not claim HTTP permission or browser workflow coverage.

## Executed verification — 7 October 2026

Started from project-data commit `b6d39fe` with a clean checkout. No models,
applied migrations, seed data or authentication flows were changed. The only
administration change makes existing account roles read-only to prevent a bypass.
Ruff also removed unused scaffold imports in projects/admin.py, tests.py and views.py,
and normalized quotes in projects/apps.py; those changes add no behavior.

Commands used the existing locked uv environment (`--cache-dir .cache/uv`).
PostgreSQL checks ran with local database access; SQLite was not used.

| Executed check | Actual result |
| --- | --- |
| Focused initial business tests | 44 passed in 4.72 seconds |
| Full `pytest -q` after all additions | 162 passed in 28.81 seconds |
| Existing tests included in full suite | All 111 passed, including 31 authentication tests |
| New business-operation cases | All 51 passed, including deactivation/membership race |
| `python manage.py check` | No issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `ruff check accounts config projects tests scripts` | Passed |
| `ruff format --check accounts config projects tests scripts` | 38 files already formatted |
| `git diff --check` | Passed |

The first broad Ruff run found three pre-existing unused scaffold imports; removed
and rechecked successfully. No remaining infrastructure blocker. Tests used Django's
separate PostgreSQL test database; development data was not reset or reseeded. No
migration application was needed, and no push or deployment was performed.

## Phase 3 adapters

Resource REST adapters now call these operations and selectors; see `api.md` for
exact routes, permissions, field parsing and error responses. Report and Overview
functions scope queries before aggregating. The existing service functions and
locking behavior remain unchanged. HTML workflow screens are the next milestone.

## HTML entry points (Phase 4A)

The desktop pages adapt the same services/selectors/reports without calling the
server's own HTTP API. Each page reloads the actor; account pages require application
Admin, project/team writes require Admin or owning Manager, and Employee project
pages are read-only. Forms reject unknown/protected keys and preserve nonsecret values
after errors. Native controls parse input; existing operations remain authoritative.
Role edits require a confirmation checkbox, password resets are optional and restore
the initial-password gate, and destructive actions show a confirmation page before
CSRF-protected POST. Eligible member options exclude existing members; service validation
still rejects a forged duplicate. No activation action is exposed. Task/time UI is implemented in Phase 4B below.


## HTML task/time adapters (Phase 4B)

`projects/task_views.py` parses forms and calls existing shared services. The project
Tasks tab uses scoped status/assignee filters; My tasks is Employee-only, scoped to
current assignments, and defaults to unfinished. Lists paginate before separately
aggregating scoped time for displayed tasks. Employee logged-time columns contain only
own original contributions; project summary metrics are explicitly labelled Own work.
Task detail reads team summaries and only authorized time details/notes.

Create/edit share TaskForm with a fixed project and active member choices. Leaving
assignee blank on edit keeps historical/inactive assignment; selecting a new assignee
still requires active membership. Employees have no detail/reassignment form. Ordinary
completed-task edits are denied; Admin uses explicit correction wording and the existing
correction service. Managers/Admin may start/complete scoped tasks under the existing
service contract; Employees only their assignments. Start is POST-only. Completion,
task deletion and time deletion require confirmation plus POST; repeated completion
remains an authorized same-status no-op.

Log/edit time share TimeForm, deriving contributor from the actor for creation. Identity
is never posted as an editable field. Employees edit/delete their own entry only while
still assigned and IN_PROGRESS. Admin time corrections may edit historical or completed
entries without changing attribution/status; Managers have read access only.

Native controls parse values, forms reject protected keys, and model/service validation
remains authoritative. Fresh service PermissionDenied returns a retained-input 403 with
completion/reassignment guidance; validation/database failure returns retained-input 200.
Protected deletion produces a controlled history-preservation error. Foreign/missing
resources return 404. All pages recheck actor activity and initial-password gating.
No new locks, models, migrations, report formulas or service architecture were added.

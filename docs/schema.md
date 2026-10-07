# Schema — authentication and project data foundations

Implemented: `accounts.User` extends Django `AbstractUser` and is selected by
`AUTH_USER_MODEL` before the first migration. Database table: `accounts_user`.
It includes the standard unique username, hashed password, name/contact fields,
active/staff/superuser flags, timestamps and standard Group/Permission relations.

Application fields:

| Field | Definition |
| --- | --- |
| role | ADMIN, PROJECT_MANAGER or EMPLOYEE; default EMPLOYEE |
| must_change_password | Boolean, default true; gates workspace/API access |

PostgreSQL checks reject unknown role values and staff/superuser flags on non-Admin
roles. The username is unique and case-sensitive. Django sessions use the standard
`django_session` table and store authentication metadata, never plaintext passwords.

The applied `accounts/migrations/0001_initial.py` and custom User remain unchanged.
The additive `projects/migrations/0001_initial.py` depends on the swappable User model;
it creates four new tables without rewriting accounts or their migration history.

## Relationships

| Parent | Child/reference | Reverse name | Deletion relationship |
| --- | --- | --- | --- |
| User (Project Manager) | Project.manager | managed_projects | PROTECT |
| Project | ProjectMembership.project | memberships | PROTECT |
| User (Employee) | ProjectMembership.employee | project_memberships | PROTECT |
| Project | Task.project | tasks | PROTECT |
| User (Employee) | Task.assignee | assigned_tasks | PROTECT |
| Task | TimeEntry.task | time_entries | PROTECT |
| User (original contributor) | TimeEntry.employee | time_entries | PROTECT |

All four entities have Django BigAutoField primary keys. Relationships are required,
non-null foreign keys to persisted records. Project membership is explicit; a task's
assignee is a User, not a membership row. A time entry references its original User
directly, so reassignment or membership removal does not transfer recorded hours.

## Field definitions

### Project — projects_project

| Field | Definition |
| --- | --- |
| name | Required non-whitespace string, maximum 200 characters; display names need not be unique |
| description | Optional text, empty string allowed |
| manager | Required User; new/changed ownership requires an active PROJECT_MANAGER |
| start_date | Required calendar date |
| end_date | Required calendar date on or after start_date; equal dates allowed |
| demo_key | Optional internal unique nullable string, maximum 64 characters; not editable in forms |

The demo key identifies sample projects independently of their editable display name.
Normal projects leave it NULL. Ordinary saves cannot change a persisted demo key.
Existing ownership survives manager deactivation; deactivation is not a history reset.

### ProjectMembership — projects_projectmembership

| Field | Definition |
| --- | --- |
| project | Required Project |
| employee | Required User; a new membership requires an active EMPLOYEE |

The (project, employee) pair is unique. Its identity cannot change through ordinary
save: remove the old membership and add a new one. Existing memberships survive
deactivation. Membership removal is blocked while unfinished tasks remain assigned.

### Task — projects_task

| Field | Definition |
| --- | --- |
| project | Required Project; immutable after creation through ordinary saves |
| title | Required non-whitespace string, maximum 200 characters |
| description | Optional text, empty string allowed |
| assignee | Required User; new assignment/reassignment requires active EMPLOYEE membership in this project |
| status | TODO, IN_PROGRESS or COMPLETED; default TODO |

New tasks must begin at TODO. Ordinary saves allow the current status as a no-op or
the next step TODO → IN_PROGRESS → COMPLETED; skipping and reopening are rejected.
An unchanged completed assignment remains valid after membership removal/deactivation.
Titles are not unique. Composite indexes support project/status and assignee/status
task summaries; Django also indexes the foreign keys.

### TimeEntry — projects_timeentry

| Field | Definition |
| --- | --- |
| task | Required Task; immutable after creation through ordinary saves |
| employee | Required original contributing User; immutable after creation through ordinary saves |
| work_date | Required calendar date, not in the future in the configured application timezone |
| minutes | Required Python integer, 1–1440 inclusive; stored as PostgreSQL smallint |
| note | Optional text, empty string allowed |

New time entries require the task to be IN_PROGRESS, the contributor to be its active
Employee assignee, and a valid project membership. Booleans, floats (including 1.0),
Decimals and numeric strings are rejected before Django can coerce/truncate them;
forms/services should produce actual integers. The limit is per entry, not a daily
capacity or overlap rule. Work date is not constrained to project dates by policy.
Existing history is validated without requiring current assignment/activity/membership.

## Database constraints versus application validation

PostgreSQL enforces required/non-null fields, foreign keys, string lengths, non-blank
project/task names, project date ordering, membership uniqueness, allowed status values,
bounded stored integer minutes, and optional demo-key uniqueness. Future work dates,
valid related roles/activity, assignment membership, initial/previous-state transitions
and immutable history identities are checked explicitly in Python; they are not
cross-table CHECK constraints or triggers.

Each project model's ordinary `save()` explicitly calls `full_clean()` inside a
transaction; `objects.create()` uses this path. For `save(update_fields=...)`, validation
uses a freshly read row plus only the fields actually being written, so unsaved or
stale values cannot validate an invalid partial update. `full_clean()` can also be
called explicitly before persistence; `clean()` is not assumed to run automatically.

Lock order for supported ordinary writes: containing Project row, then the updated
entity row. The project lock serializes assignment, status/time saves and membership
removal. Multi-project membership deletion locks Project IDs in ascending order,
then selected membership rows in ascending primary-key order, rechecks unfinished
assignments and deletes only the checked rows. Two real PostgreSQL competing-operation
tests verify both assignment-first and removal-first outcomes.

`QuerySet.update()`, bulk_create/bulk_update and raw SQL bypass model validation and
these save locks. They must not be used for future application mutations without an
explicit validated operation. Database constraints still protect their row-level
invariants. Account role/activity changes use guarded shared operations; see `business-rules.md`
for the User-before-Project lock order at the application boundary.

## Deletion policy

- Projects with memberships or tasks are protected; remove eligible memberships and
  dependent tasks explicitly before deleting a project. A truly empty project is deletable.
- Tasks with time entries are protected, including queryset deletion. Tasks without time
  history are deletable at the trusted data layer; shared services enforce actor/status permissions.
- Users referenced as managers, members, assignees or contributors are protected.
  Deactivate accounts instead of deleting work/history.
- Membership instance and queryset deletion reject unfinished assignments. Removal after
  completion/reassignment preserves tasks and original time contributions.
- Time entries are leaf records. Trusted data-layer deletion is possible, but never
  cascaded from projects/tasks/users. Shared operations restrict normal-user edits
  and deletes on completed work and expose intentional Admin corrections explicitly.

PROTECT is Django's collector policy. PostgreSQL foreign keys independently reject
orphan references; raw SQL is not authorized to bypass the documented deletion policy.
The new models are not registered as writable Django Admin resources in this phase.

## Application boundary

Phase 2 shared functions now enforce ownership, field whitelists, completed-record
locks, scoped reads, Admin corrections and guarded account role changes. See
`business-rules.md` for the contract. Models themselves still have no actor; callers
must use the operations for application mutations. No resource pages/APIs are exposed.

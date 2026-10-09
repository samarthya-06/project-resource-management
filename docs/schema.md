# Database schema

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




# REST API and authentication

Session authentication and assignment resource APIs are implemented. All API routes
require an active authenticated account whose initial password has been changed.
Application Admin authorization uses the stored ADMIN role; superuser/staff flags
are not required and are never application-editable.

| Route | Method | Behaviour |
| --- | --- | --- |
| /login/ | GET, POST | HTML form; CSRF-protected Django session login |
| /logout/ | POST | CSRF-protected session logout; redirect to login |
| /password/change/ | GET, POST | HTML form; old password + new password/confirmation |
| / | GET | Authenticated foundation landing page |
| /api/auth/me/ | GET | Current account identity only |

`/api/auth/me/` example:

```json
{"id": 4, "username": "asha@demo.local", "name": "Asha Deshmukh", "role": "EMPLOYEE", "role_label": "Employee"}
```

- No session, inactive account or initial password pending: API returns 403.
- Authenticated, initial password changed: current-user GET returns 200, with no-store caching.
- Mutations to current-user endpoint: 405 for an authenticated user (or 403 if CSRF
  validation rejects a state-changing request first). No writable role/identity fields.
- Anonymous HTML pages redirect to login with a local `next` destination. External
  destinations are rejected. Login failures return the same generic HTML error (200),
  retain the login identifier and clear the password.
- Missing/invalid CSRF on login, password change or logout: 403. GET logout: 405
  for an authenticated account. Successful login/password change/logout redirect (302).
- Password validation failure: HTML form (200) with field errors; password remains
  unchanged. Initial-password lock persists. Successful change clears that lock and
  invalidates other sessions; current session remains signed in.

Use the shared login page to obtain a session and CSRF cookie. Send cookies on
same-origin requests; API mutations require `X-CSRFToken`. Login rotates the CSRF
cookie, so read the current token after login. BasicAuth, JWT and public signup are
not configured. Existing authentication routes and password behavior are preserved.

## Resource routes

All paths have trailing slashes. IDs are integer primary keys. GET detail and lists
return 200; POST creation returns 201; successful updates/corrections/deactivation
return 200; successful DELETE returns 204 with no body. Unsupported methods are 405.
All mutations use the existing shared service functions, not serializer/model saves.

| Route | Methods | Permission / behavior |
| --- | --- | --- |
| /api/accounts/ | GET, POST | Admin lists/provisions accounts |
| /api/accounts/{id}/ | GET, PUT, PATCH | Admin views/edits profile, role or password |
| /api/accounts/{id}/deactivate/ | POST | Admin deactivates; body `{}`; preserves history |
| /api/projects/ | GET, POST | Scoped list; Admin/Manager creates |
| /api/projects/{id}/ | GET, PUT, PATCH, DELETE | Scoped detail; Admin/owner manages; safe deletion |
| /api/projects/{id}/memberships/ | GET, POST | Scoped team IDs; Admin/owner adds Employee |
| /api/projects/{id}/memberships/{employee_id}/ | DELETE | Admin/owner removes by Employee ID, not membership ID |
| /api/projects/{id}/employee-options/ | GET | Admin/owner selects active Employees; minimal id/name |
| /api/tasks/ | GET, POST | Scoped team tasks; Admin/owner creates |
| /api/tasks/{id}/ | GET, PUT, PATCH, DELETE | Scoped detail; Admin/owner edits; assignee status-only |
| /api/tasks/{id}/correction/ | PATCH | Explicit Admin correction of completed task details |
| /api/time-entries/ | GET, POST | Scoped time details; Employee creates own time |
| /api/time-entries/{id}/ | GET, PUT, PATCH, DELETE | Scoped detail; Employee edits/deletes own eligible entry |
| /api/time-entries/{id}/correction/ | PATCH | Explicit Admin time correction retaining attribution |
| /api/projects/{id}/report/ | GET | Scoped project report; Employee sees own work |
| /api/overview/ | GET | Role-scoped summary; Employee sees own work |

Project scope: Admin all; Manager owned; Employee membership projects. Tasks follow
that project scope, including team task summaries for Employees. Time detail scope:
Admin/owning Manager project time; Employee only own entries in membership projects.
Foreign records and another Employee's detailed time entries are unavailable (404).
Former members lose access to project contributions; history stays with the project.
Employee picker includes already assigned members as well as other active Employees;
duplicate additions remain a validation error. Options contain only `id` and `name`.

## JSON input and writable fields

Mutations use `Content-Type: application/json`. Resource write views accept JSON only;
other body formats return 415. Unknown/protected fields return 400, never silently
ignored. DELETE and deactivation accept an empty body or `{}` only. Related IDs and
minutes must be JSON integer numbers; booleans, fractional numbers (including 1.0),
numeric strings and null are rejected. Strings/dates are parsed by DRF; business
validation is performed by services/models.

| Operation | Fields |
| --- | --- |
| Account create | username and password required; email, first_name, last_name, role optional (default EMPLOYEE) |
| Account update | username, email, first_name, last_name, role, password |
| Project create | name, start_date, end_date required; description optional; Admin must supply manager_id |
| Project update | name, description, start_date, end_date; manager_id only Admin |
| Membership add | employee_id required |
| Task create | project_id, title, assignee_id required; description optional; always begins TODO |
| Task update Admin/owner | title, description, assignee_id, status |
| Task update Employee | status only, for assigned task |
| Completed-task correction | title, description, assignee_id; no status/project changes |
| Time create | task_id, work_date, minutes required; note optional; employee derived from actor |
| Time update/correction | work_date, minutes, note; task/contributor immutable |

PUT deliberately uses the same partial-update semantics as PATCH for this assignment:
omitted fields retain stored values. It is not full replacement. `{}` checks current
permissions/model validity and changes nothing on editable records. Use POST for
creation; its required fields cannot be omitted. Managers cannot supply manager_id,
even their own. An existing task's project_id and time entry's task_id are rejected
on updates. Staff/superuser flags, groups, permissions, password hashes, demo_key,
primary keys and must_change_password are never writable.

Account passwords are Django-validated/hashed, never returned. Creation/reset sets
the initial-password-change gate. Role changes reject owned projects, memberships or
unfinished assignments and explain reassignment/removal prerequisites. Deactivation
preserves references and revokes access. Reactivation is not implemented.

Tasks move TODO → IN_PROGRESS → COMPLETED one step at a time. Same-status repetition
is a no-op. Normal completed edits/reassignment/deletion are denied, including time
edits/deletes. Admin correction does not reopen the task. Completed task deletion
is unavailable even to Admin. Time writes require the Employee's own entry and
current assignment/membership on an IN_PROGRESS task. Managers cannot mutate time.
Admin correction changes existing entries, cannot forge contributors or create work
on behalf of an Employee. Time uses whole minutes 1–1440 and nonfuture work_date.

## Pagination and filters

Every resource list, membership list and employee picker returns this shape with
25 rows per page, ordered by ascending primary key. Use `?page=2`; invalid pages
return 404. Page size is fixed. Foreign scope is applied before filtering/pagination.

```json
{"count": 1, "next": null, "previous": null, "results": [{"id": 4, "name": "Asha Deshmukh"}]}
```

Tasks support combined `project`, `status` and `assignee` filters:
`/api/tasks/?project=1&status=IN_PROGRESS&assignee=4`.
Status is TODO, IN_PROGRESS or COMPLETED. IDs must be positive integer query values.
Time supports `project` and `task`: `/api/time-entries/?project=1&task=2`.
Filters also apply to task/time detail lookups if provided. Valid foreign filter IDs
produce an empty list, never wider scope; malformed supported filters return 400.
Other query parameters are ignored. Accounts/projects/memberships/picker have no
additional filters in this phase. Reports have no client-controlled scope filters.

## Request and response examples

After signing in through `/login/`, use the session cookie and current CSRF cookie:

```javascript
const csrf = decodeURIComponent(document.cookie.split('; ')
  .find(cookie => cookie.startsWith('csrftoken=')).split('=')[1]);
const response = await fetch('/api/projects/', {
  method: 'POST', credentials: 'same-origin',
  headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
  body: JSON.stringify({name: 'Website', start_date: '2026-10-06', end_date: '2026-10-23'})
});
const project = await response.json();
```

Manager project response (201):

```json
{"id": 1, "name": "Website", "description": "", "manager_id": 2, "start_date": "2026-10-06", "end_date": "2026-10-23"}
```

POST `/api/projects/1/memberships/` with `{"employee_id":4}` returns (201):

```json
{"id": 1, "project_id": 1, "employee_id": 4}
```

POST `/api/tasks/` with `{"project_id":1,"title":"Homepage","assignee_id":4}`
returns (201):

```json
{"id": 2, "project_id": 1, "title": "Homepage", "description": "", "assignee_id": 4, "status": "TODO"}
```

As the assigned Employee, PATCH `/api/tasks/2/` with `{"status":"IN_PROGRESS"}`,
then POST `/api/time-entries/`:

```json
{"task_id":2,"work_date":"2026-10-06","minutes":45,"note":"Homepage layout"}
```

Time response (201):

```json
{"id":1,"task_id":2,"employee_id":4,"work_date":"2026-10-06","minutes":45,"note":"Homepage layout"}
```

PATCH `/api/tasks/2/` with `{"status":"COMPLETED"}`. Admin may later PATCH
`/api/tasks/2/correction/` with `{"title":"Homepage layout"}` or
`/api/time-entries/1/correction/` with `{"minutes":50,"note":"Corrected duration"}`.

Admin POST `/api/accounts/`:

```json
{"username":"new.employee","first_name":"New","role":"EMPLOYEE","password":"Example-Initial!927"}
```

Account response (201; no password or privilege flags):

```json
{"id":8,"username":"new.employee","first_name":"New","last_name":"","email":"","role":"EMPLOYEE","is_active":true}
```

## Report definitions

Task counts and recorded time are aggregated separately; multiple entries cannot
multiply task counts. Status counts include zero-valued statuses. Percentages are
completed / total × 100, zero for an empty task set. Minutes are exact integers;
hours = minutes / 60. Hours/percentages round to two decimal places using decimal
half-up rounding, matching PostgreSQL ROUND. These are recorded hours, not capacity,
budget or productivity metrics. Work date is not filtered to project dates.

Admin/Manager project response after the example's 45 minutes:

```json
{
  "project_id":1,"scope":"project","scope_label":"Project work",
  "task_counts":{"TODO":0,"IN_PROGRESS":0,"COMPLETED":1},
  "total_tasks":1,"completed_tasks":1,"completion_percentage":100.0,
  "total_minutes":45,"total_hours":0.75,
  "contributors":[{"employee_id":4,"name":"Asha Deshmukh","minutes":45,"hours":0.75}]
}
```

Contributors use original TimeEntry.employee, including inactive/former members and
contributors whose tasks were reassigned. No time notes appear in reports. Empty
projects return zero metrics and an empty contributors list.

Employee project responses have scope `own_work`, label `Own work`, task counts for
their current assignments and time for their original contributions in that membership
project (including reassigned-task history). These are separate measures; recorded
time need not belong to currently assigned tasks. Other contributors are excluded.

Overview returns scope, scope_label, project_count and the same metric fields without
project_id/contributors. Admin/Manager scope is `authorized_projects`; Employee scope
is `own_work`, labelled `Own work in membership projects`. project_count counts visible
projects, including empty ones. Employee task/time metrics are only their own work.

The read-only `sql/project_reports.sql` contains full-database review queries for
per-project metrics and original contributor hours. It is never an unscoped endpoint.
Reproduce comparison on the existing seeded PostgreSQL database:

```bash
uv run python manage.py shell -c 'from scripts.verify_project_reports import verify; print(verify())'
```

## Errors and tested status codes

| Status | Meaning |
| --- | --- |
| 400 | Invalid/unknown/protected fields, failed model/service validation, guarded role/membership changes, protected deletion |
| 403 | Anonymous/inactive/initial-password account, missing/invalid CSRF, role/action forbidden or completed mutation lock |
| 404 | Missing/out-of-scope record or private Employee time detail; invalid page also 404 |
| 405 | Unsupported method, including account DELETE |
| 415 | Unsupported mutation content type |

Examples:

```json
{"minutes":["Use a JSON whole integer, not a boolean, fraction or string."]}
```

```json
{"end_date":["End date must be on or after start date."]}
```

```json
{"detail":"Completed tasks are read-only; Admin must use a correction."}
```

Missing/foreign resource detail consistently returns `{"detail":"Resource unavailable."}`.
Protected deletion returns 400 `{"detail":"Dependent work or history prevents deletion."}`.
General model errors use `non_field_errors` or Django's `__all__` key; clients should
show both as form-wide errors. Role-specific forbidden fields return 400. An action
forbidden by role on an otherwise visible record returns 403. There is no universal
401 guarantee with SessionAuthentication. Authentication/CSRF checks happen before
view logic, so those 403 errors may take precedence over payload/method errors.

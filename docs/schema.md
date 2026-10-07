# Current schema — authentication foundation

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

The initial migration depends on Django auth migrations and is in
`accounts/migrations/0001_initial.py`. Model migration and database checks were executed
on PostgreSQL 17.11. Project, ProjectMembership, Task and TimeEntry are still planned;
there are no implemented project relationships or report queries yet.

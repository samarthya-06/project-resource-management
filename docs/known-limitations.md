# Current limitations

As of the project data foundation milestone:

- Implemented: PostgreSQL configuration/migrations, custom roles, session login,
  initial-password gate, password change, POST logout, inactive-session rejection,
  read-only identity API, four project data models with explicit validation/protected
  relationships and idempotent development account/project seeding.
- The Overview is a foundation landing page, not the finished Paper dashboard.
  Project permission/mutation services, report queries, resource APIs and screens remain pending.
- Ordinary saves enforce structural rules and forward statuses. Actor-aware completed-record
  locks, explicit Admin corrections, scoped reads and coordinated account role/activity changes
  must be implemented before resource write endpoints. Bulk writes bypass cross-table validation.
- Account provisioning currently uses bootstrap superuser development administration.
  Application account management outside Django Admin will be added with the Employees UI.
- Credential handoff is manual/private. Public signup, email invitations and email password
  recovery are outside the current implementation. A bootstrap Admin can reset credentials.
- Login has no application rate limiting yet. This is a local assignment foundation,
  not a deployment readiness claim.
- Paper's login measurements were exported; implementation uses required IBM Plex Sans
  in place of the accidental system-font layers on that artboard. Exact whole-screen
  visual parity and the remaining desktop screens are pending.
- The user excluded mobile design artifacts. Browser responsiveness and full keyboard/
  accessibility review of the finished application have not been completed.
- Required manual cases, workflow/security tests beyond authentication, SQL reports and
  full clean-checkout submission rehearsal remain pending. Automated tests do not replace
  the company's required manual test evidence.
- No deployment or submission was performed. `.env` contains generated local credentials
  and remains ignored; local database role has CREATEDB solely for testing.

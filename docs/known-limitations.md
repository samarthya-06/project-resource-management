# Current limitations

As of Phase 3 resource APIs and basic reports:

- Implemented: PostgreSQL configuration/migrations, custom roles, session login,
  initial-password gate, password change, POST logout, inactive-session rejection,
  read-only identity API, four project data models with explicit validation/protected
  relationships and idempotent development account/project seeding.
- The Overview is a foundation landing page, not the finished Paper dashboard.
  Resource APIs and scoped task/time reports are implemented; the designed screens remain pending.
- Ordinary saves enforce structural rules and forward statuses. Shared operations enforce
  completed-record locks, explicit Admin corrections, scoped reads and guarded account changes.
  Resource endpoints now call them. Bulk writes bypass cross-table validation.
- Account provisioning has Admin-only shared operations and bootstrap development administration.
  Admin account REST management exists; the Employees UI remains pending.
- Credential handoff is manual/private. Public signup, email invitations and email password
  recovery are outside the current implementation. A bootstrap Admin can reset credentials.
- Login has no application rate limiting yet. This is a local assignment foundation,
  not a deployment readiness claim.
- Paper's login measurements were exported; implementation uses required IBM Plex Sans
  in place of the accidental system-font layers on that artboard. Exact whole-screen
  visual parity and the remaining desktop screens are pending.
- The user excluded mobile design artifacts. Browser responsiveness and full keyboard/
  accessibility review of the finished application have not been completed.
- Required manual cases and full clean-checkout submission rehearsal remain pending.
  HTTP workflow/security tests and SQL/report comparisons are automated; browser UI work is pending.
  Automated tests do not replace the company's required manual test evidence.
- No deployment or submission was performed. `.env` contains generated local credentials
  and remains ignored; local database role has CREATEDB solely for testing.

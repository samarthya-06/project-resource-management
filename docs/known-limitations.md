# Current limitations

As of Phase 4B complete desktop workflow, 8 October 2026:

- Implemented: PostgreSQL models/constraints/migrations, guarded shared operations,
  session authentication and initial-password change, role-scoped REST APIs/reports,
  read-only SQL comparisons and deterministic idempotent demo data.
- Desktop UI now includes the shared header/sidebar, real role Overview metrics,
  Admin account list/search/create/edit/deactivate, project list/search/create/edit,
  project Overview/Team/Report and guarded membership add/remove. Existing password
  change keeps the centered authentication layout and adds accessible save/error feedback.
- Task/time UI now includes scoped Project Tasks and My tasks filters, create/edit/
  reassignment, role-specific task details, start/confirmed completion, own time create/
  edit/confirmed deletion, safe task deletion and explicit Admin corrections. All writes
  reuse services. Completed work remains locked; historical attribution is retained.
- Safe project deletion is supported by services/API, without a Phase 4A UI action.
  There is no account reactivation operation; inactive rows offer Edit only.
- Credential handoff is private/manual. Public signup, invitations and email password
  recovery are outside scope. Application Admin can reset passwords from Employees.
- Account names/contact email remain optional to match existing backend contracts;
  login identifier, role and initial password are required. Native date inputs follow
  browser locale; displayed record dates use readable day/month/year text.
- Paper and exported PNGs were compared with rendered desktop screenshots, but no
  exact pixel-parity claim is made. IBM Plex Sans replaces incidental system-font
  layers, actual database totals replace design samples, and accessibility/real forms
  introduce visible changes. See `workspace-ui-verification.md` and `task-ui-verification.md` for differences.
- Chromium keyboard checks and 200% zoom-equivalent reflow were executed. Native
  browser-menu zoom, screen-reader review, complete contrast audit and other browsers
  were not manually tested. Mobile design/layout verification is excluded by the user.
- Required human manual cases and a full clean-checkout submission rehearsal remain
  pending. Thirty manual cases are drafted in `manual-test-cases.csv`, all NOT RUN.
  Automated browser/HTTP/SQL checks do not replace manual evidence.
- Login has no application rate limiting. This assignment is not a deployment
  readiness claim. `.env` stays ignored; no deployment, submission or database reset.
- Bulk ORM/raw writes bypass cross-table validation; application mutations must keep
  using shared operations rather than introducing direct model writes.

- Task time history is shown without pagination (small assignment data); task lists
  paginate 25 rows. Dates are manual durations, without timers, overlap detection or
  daily capacity limits. Former members lose access to old project contributions,
  while Manager/Admin history remains available. This preserves existing policies.
- Failed inline time saves render the shared full-page Log time form with retained values.
  Browser reflow tables scroll horizontally inside a focusable region at 200% equivalent
  zoom; this is not mobile layout support. No live notifications or stale-state polling.

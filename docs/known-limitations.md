# Known limitations

Current scope: the desktop Project & Resource Management assignment workflow.

## Product scope

- Time uses manually entered Hours/Minutes and a work date. There is no timer,
  overlap detection, daily capacity limit or resource forecasting.
- Account deactivation preserves history. Account reactivation, public signup,
  email invitations and email password recovery are not implemented. Admin can
  explicitly reset a password through Employees.
- Login has no application rate limiting.
- Project deletion is available through guarded services/API; there is no desktop
  project-delete button. Dependent work is protected from destructive deletion.
- Task lists paginate 25 rows; a task's time history is not paginated.
- Names/contact email are optional. Date inputs follow browser locale; displayed
  records use readable day/month/year dates.
- Former members lose access to their old project contributions. Original history
  remains visible to the owning Manager and Admin.
- Failed inline time saves use the full-page Log time form with retained values.
  There are no live notifications or stale-state polling.
- Bulk ORM or raw SQL writes can bypass cross-table validation. Application writes
  must use the shared services; the application UI/API do so.

## Interface differences

IBM Plex Sans is used consistently. Native date/select/number controls, persistent
labels, link underlines, validation summaries and full-page confirmations support
the working forms. Employee reports show Own work to preserve privacy. Tables can
scroll within their regions when space is limited. Mobile design is outside scope.



See [testing and results](testing.md) for executed outcomes, evidence and the resolved
static-file test setup defect, and [deployment](render-deployment.md) for hosting setup.

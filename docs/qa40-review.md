# Local 40-case QA execution record

Review date: 9 October 2026. Application commit: `ea0366bab91eb5d37b53a416635f303b447e5435`.
Execution method: automated checks using pytest, Playwright Chromium and PostgreSQL
verification. These results are separate from human manual testing.

The results sheet contains **40 PASS and 0 FAIL**. M39 verifies Overview visibility
before and after the assigned Employee uses Start task. Admin and Manager project
totals include the new project immediately; their Work in progress tables include
its task only after it reaches IN_PROGRESS. The Employee sees their own TODO task,
and a foreign Manager cannot see it. This matches the user's local observation.
All 40 executable test functions passed. The existing 284-test PostgreSQL regression
suite passed in a separate invocation. No application behavior was changed for this
case. Test mutations used isolated fixtures, not development or hosted records.

## Deliverables

Cases are grouped by the assignment categories. See [requirement coverage](testing-requirement-coverage.md)
and the workbook’s Requirement coverage tab. Scenario type distinguishes positive, negative
and combined cases; all original IDs, outcomes and evidence are retained.

- [Full results CSV](qa40-results.csv): requirement mapping, preconditions, steps,
  data, expected/actual results, status, priority, evidence and execution date.
- [Results workbook](qa40-results.xlsx): summary, case information,
  requirement coverage and SQL comparison.
- [Defects and unverified checks](qa40-defects.md).
- [Evidence directory](evidence/qa40/): case JSON request/assertion logs,
  screenshots and JUnit execution records. Each results-sheet row names its evidence.
- [Human manual-case template](manual-test-cases.csv): the same 40 cases with
  blank actual results and NOT RUN status, for subsequent human execution.

## Environment and isolation

The app ran locally through pytest-django's live server, with Playwright Chromium
at a 1440×900 CSS viewport. Each case received fresh seeded fixtures in the isolated
PostgreSQL test database. Fixtures covered Admin, two Managers, two project
Employees, an inactive Employee, an unrelated Employee, separately owned projects,
empty projects and all three task states. Test mutations did not use development
or Render records. Passwords are redacted in request logs.

Seeding ran in the explicitly permitted development mode; case execution used
`DEBUG=False` to verify generic unavailable responses. The test live server served
source static assets with `StaticFilesStorage`; the production hashed asset build,
HTTPS proxy configuration and hosted database were not exercised. Development
debug 404 pages were excluded from final evidence after the harness was corrected.

The review uses browser interaction for visible workflows and the browser's
authenticated HTTP client for direct URL/API, malformed input, CSRF and forbidden
mutation checks. ORM/SQL readback verifies persistence and unchanged protected
records. Source code is not changed to force a passing outcome. M10 injects a
test-only `DatabaseError` to verify failed-save retention; this is a controlled
simulation, not a discovered application failure.

## Coverage

| Cases | Scope |
| --- | --- |
| M01–M08 | Authentication, password-change gate/reset, account validation, role guards, deactivation and history preservation |
| M09–M16 | Project validation/persistence, scoped access, active membership selection, removal/reassignment guards and retained attribution |
| M17–M23 | Task creation/edit/filters, no eligible members, status transitions, confirmation and completed-task lock |
| M24–M29 | Hours/minutes boundaries, future dates, own entry edit/delete, ownership and stale completion/reassignment |
| M30–M33 | Scoped reports/Overview, Admin corrections, SQL agreement and historical contributors |
| M34–M38 | REST workflow/validation, forged fields, data isolation, CSRF, stored script escaping and literal search input |
| M39 | Overview project totals and task visibility before/after Start task, including foreign Manager isolation |
| M40 | Protected history and allowed empty-record deletion |

Expected negative outcomes were exercised: bad passwords, duplicate identifiers,
reversed dates, invalid members/durations, forbidden updates, missing CSRF tokens
and stale-state requests. Rejection with retained valid values or unchanged records
is a passing negative test. These outcomes do not belong in an application defect list.

## SQL/report agreement

Both read-only queries in `sql/project_reports.sql` were executed and compared
with scoped application reports, including after reassignment. M33 records exact
SQL rows and the comparison result: MATCH across four projects and four non-null
project/contributor pairs. Projects without tasks/time were retained.

| Project | Tasks | TODO | In progress | Completed | Completion | Minutes | Hours |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Client Website Redesign | 6 | 2 | 2 | 2 | 33.33% | 720 | 12 |
| Employee Onboarding Portal | 5 | 2 | 1 | 2 | 40% | 720 | 12 |
| Internal Knowledge Base | 0 | 0 | 0 | 0 | 0% | 0 | 0 |
| Operations Handbook | 1 | 1 | 0 | 0 | 0% | 0 | 0 |

Original contributor totals remained Asha 420 minutes / Ravi 300 minutes on
Website Redesign and Asha 360 / Ravi 360 on Onboarding. M30 independently checked
a three-task fixture with two completed tasks, 180 minutes, 3 hours and 66.67%
completion. M32 checked Admin correction of completed work without reopening or
changing time attribution.

## Executed checks and reproduction

Run from the repository root with the README PostgreSQL setup and browser
dependencies installed:

```bash
uv run pytest tests/test_submission_review.py -q
uv run pytest --ignore=tests/test_submission_review.py -q
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check accounts config projects tests scripts
```

The case suite passed 40 executable tests in 134.53 seconds; its JUnit record is
`evidence/qa40/junit.xml`. The separately executed existing regression suite passed
284 tests in 80.29 seconds (`regression-junit.xml`). Django reported no issues,
migration checking reported no changes, and Ruff lint/format checks passed.
These are two runs covering 324 unique tests, not a claim of a single 324-test run.

Representative screenshots: [duplicate account validation](evidence/qa40/M05-final.png),
[stale-state rejection](evidence/qa40/M29-final.png),
[completed correction](evidence/qa40/M32-final.png),
[generic unavailable response](evidence/qa40/M16-final.png) and
[Admin Overview after Start task](evidence/qa40/M39-admin-after-start.png).
See the [complete evidence index](evidence/qa40/index.md) for the exact captured files.

To intentionally replace case evidence, run:

```bash
QA40_EVIDENCE=1 uv run pytest tests/test_submission_review.py -q --junitxml=docs/evidence/qa40/junit.xml
```

This replaces JSON/screenshots; regenerate the human-readable sheets afterward
before claiming they match a new run. Existing regression browser tests also write
their own evidence paths. Original tracked screenshots were preserved/restored
after this review's regression invocation, including the pre-existing user change.

## Remaining verification

Native 200% browser zoom/human usability, other browsers, a full screen-reader or
contrast audit and hosted-site checks remain unverified. A subsequent fresh-checkout
setup smoke check passed with installed tools; see `readme-setup-verification.md`.
Installer instructions and Windows remain unverified. This is scoped functional/security QA, not a complete penetration
test. Existing limitations such as missing login rate limiting remain documented
in `known-limitations.md`. No confirmed application defect was found in this
executed scope; this does not establish that the application is defect-free.

# Testing and results

The forty test cases were executed manually, with separate automated checks using
pytest, Playwright Chromium and an isolated PostgreSQL database. Samarthya
Jambavalikar confirmed on 9 October 2026 that all forty manual cases matched their
expected results. The manual CSV records 40 PASS, with actual-result summaries
based on that confirmation. The earlier automated logs and workbook remain separate.

## Cases grouped by the assignment requirements

| Category | Cases | IDs |
| --- | ---: | --- |
| Authentication and accounts | 8 | M01, M02, M03, M04, M05, M06, M07, M08 |
| Project and task workflows | 17 | M09, M10, M11, M13, M14, M15, M16, M17, M18, M19, M20, M22, M24, M25, M26, M27, M39 |
| API test cases | 2 | M34, M37 |
| Permission and security | 10 | M12, M21, M23, M28, M29, M32, M35, M36, M38, M40 |
| Reports and SQL | 3 | M30, M31, M33 |

Total: **40 cases**. API calls and permission checks also occur within workflow cases;
the primary categories do not limit each case to one requirement.

## Files to review

| File | Purpose |
| --- | --- |
| [Manual cases](manual-test-cases.csv) | Forty manually executed cases with steps, expected/actual results and PASS status. |
| [Results workbook](qa40-results.xlsx) | Completed recorded results, case details, category coverage and SQL comparison. |
| [Evidence index](evidence/qa40/index.md) | Screenshots and request/assertion logs for the forty cases. |
| [SQL queries](../sql/project_reports.sql) | Read-only project status/completion/hour and original contributor totals. |

Positive and negative scenarios are included within these forty cases, rather than
being forty cases per category. Expected rejection is a passing negative result;
it does not by itself indicate a defect.

## Recorded verification

| Check | Actual result | Evidence |
| --- | --- | --- |
| Manual run | 40 PASS, 0 FAIL; confirmed by Samarthya Jambavalikar on 9 October 2026 | [Manual results](manual-test-cases.csv) |
| Forty-case browser/HTTP review | 40 passed in 134.53 seconds; 40 recorded PASS, 0 FAIL | [JUnit](evidence/qa40/junit.xml) and case logs |
| Existing PostgreSQL regression suite | 284 passed in 80.29 seconds in a separate invocation | [JUnit](evidence/qa40/regression-junit.xml) |
| Complete suite after static-file test setup fix | 324 passed in one invocation, 218.22 seconds | [JUnit](evidence/test-setup/staticfiles-regression.xml) |
| Deployment tests from the main Developer checkout | 4 passed in 0.90 seconds | Static-file fix retest |
| SQL versus application reports | MATCH for four projects and four contributor pairs | [M33](evidence/qa40/M33.json) |
| Django system check and migration drift | No issues; no changes detected | Recorded local checks |
| Ruff lint/format and Git whitespace | Passed | Recorded local checks |
| Fresh-checkout setup smoke check | Locked installation, migrations, sample seed, database reads, SQL comparison and Admin login/Overview passed | Separate disposable PostgreSQL database; installed tools |

The first two runs covered 324 unique tests separately. The later complete-suite
run verifies all 324 together. This documentation consolidation is not a new test
execution and does not change the original workbook outcomes.

## Environment and coverage

The browser review used a 1440×900 CSS viewport and pytest-django's local live server.
Fresh fixtures included Admin, two Managers, project Employees, inactive and unrelated
Employees, separately owned projects, empty projects and all three task states.
Mutations used test fixtures; development and hosted records were not reset.

Visible journeys used browser forms. Direct-URL, API, malformed-input, CSRF and
forbidden-write checks used the browser's authenticated HTTP client. PostgreSQL
readback checked persistence, protected records and original time attribution.
Password values are redacted in the logs. M10 uses a test-only DatabaseError to
exercise failed-save retention; its screenshot is an intentional simulation.

Coverage includes login/password change, accounts, project dates, membership,
task assignment and status, completion locks, Hours/Minutes validation, own time
edit/delete, stale forms, scoped reports, Admin corrections, CSRF, forged fields,
stored-script escaping and safe deletion. The functional checks are not a complete
penetration test or a guarantee that no defects exist.

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

## Defects and retests

No application defect was confirmed by the executed forty-case review.


## Run the checks

Complete the README PostgreSQL setup and install Chromium, then run:

```bash
uv run playwright install chromium
uv run pytest
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check accounts config projects tests scripts
```

The tests collect static assets automatically in a temporary directory. PostgreSQL
tests use a separate test database; the local database role needs CREATEDB.
Run only the additional forty cases with:

```bash
uv run pytest tests/test_submission_review.py -q
```

To intentionally regenerate case JSON/screenshots:

```bash
QA40_EVIDENCE=1 uv run pytest tests/test_submission_review.py -q --junitxml=docs/evidence/qa40/junit.xml
```

That command does not regenerate the CSV or workbook. Preserve existing evidence
before rerunning browser tests, and reconcile results before publishing a new record.

## Manual results and remaining verification

The completed manual results are recorded in the CSV. For a future run, use
separate disposable local accounts and project names.
Use Admin, two Managers, project Employees and an unrelated Employee; record actual
IDs for direct-URL/API checks. Follow [API authentication and CSRF examples](api.md)
using browser developer tools or a manually operated HTTP client. For each executed
case, enter the actual result, PASS/FAIL, evidence filename and any defect. Never
include passwords or session cookies in evidence.

Manual case outcomes above reflect the tester’s confirmation. Additional native
browser-menu 200% zoom, human usability, other-browser and screen-reader checks,
installer instructions/Windows setup and a complete hosted workflow retest remain
unverified. Keyboard checks and zoom-equivalent Chromium reflow were automated.
The Render site is deployed; deployment is separate from hosted test verification.
See [known limitations](known-limitations.md) for the product scope and open gaps.

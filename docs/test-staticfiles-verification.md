# Static asset test setup verification

Date: 9 October 2026.

## Confirmed setup defect

The user reported 59 failed and 225 passed tests on a checkout without a
`staticfiles/` directory. Production-mode templates raised
`ValueError: Missing staticfiles manifest entry for css/auth.css`.
The missing asset build also prevented the anonymous CSS-serving test from passing.

An independent reproduction set STATIC_ROOT to a new empty temporary directory.
The HTTPS-login and collected-CSS tests both failed with the reported manifest error.
This was a missing test prerequisite, not a failure of the task or permission rules.

## Fix

`tests/conftest.py` now runs collectstatic once per pytest session into a temporary
directory. It uses the existing production asset storage and leaves development
collected files intact. The deployment test verifies that a manifest exists and
that the hashed CSS URL returns 200 anonymously under DEBUG=False.

Production settings, deployment build commands, migrations and business behavior
are unchanged. The final submitted workbook was not edited.

## Executed checks

| Check | Actual result |
| --- | --- |
| Empty STATIC_ROOT reproduction before fix | 2 failed with missing-manifest errors |
| Deployment tests with empty initial STATIC_ROOT after fix | 4 passed in 0.90 seconds |
| Complete PostgreSQL/browser suite after fix | 324 passed in 218.22 seconds |
| Deployment tests after transferring fix to main Developer checkout | 4 passed in 0.90 seconds |
| Django system check | No issues |
| Migration drift and database history check | No changes detected |
| Ruff lint and format | Passed |
| Git whitespace check | Passed |

The complete suite ran in the Codex checkout before the user requested a move to
the main Developer folder. The subsequent four-test check ran from the main folder.
All further work uses the main folder. Tests used isolated PostgreSQL fixtures;
development and hosted records were not reset or seeded.

The complete-suite JUnit record is in `evidence/test-setup/staticfiles-regression.xml`.
These are automated verification results, not personal manual testing evidence.

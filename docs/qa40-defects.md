# Local QA review: defects and unverified work

Review date: 9 October 2026. Application commit: `ea0366b`.
Execution: agent-executed local Chromium browser/HTTP checks with PostgreSQL readback.

No application defects were confirmed by the executed 40-case review or the existing
284-test PostgreSQL regression suite. This is a statement about the checked scope,
not a claim that the application has no defects. No application fixes were made.

| ID | Related case | Classification | Observation | Evidence | Next action |
| --- | --- | --- | --- | --- | --- |
| QA40-U02 | All | Unverified | This review used the local app and isolated test database. It did not verify the hosted Render app or hosted database. | `qa40-review.md` | Repeat the critical workflow and permission checks on the deployment with disposable accounts. |

The failed-save screenshot in M10 is an intentional test-only database-error
simulation. Invalid credentials, duplicate identifiers, bad dates/durations,
membership-removal guards, CSRF failures and stale-state rejections are expected
negative outcomes. They are passing tests, not application defects.

Existing limitations remain documented in `known-limitations.md`, including no
application login rate limiting, no account reactivation and no automatic timer.
Rate limiting and broader penetration testing were not newly tested in this review.

For a future confirmed defect, record: defect ID, case/requirement, severity, account
role, preconditions, exact steps and request data, expected/actual outcome, screenshot
or response evidence, fix reference and retest result. Keep a defect open until its
fix has been retested. Do not invent a defect merely to provide a negative scenario.

M39 confirms expected Overview behavior: Admin/Manager Work in progress excludes
TODO tasks and includes them after the assigned Employee clicks Start task. Project
counts update immediately. The user's observation was reproduced with isolated
fixtures and is a passing workflow case, not a confirmed defect.

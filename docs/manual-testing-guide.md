# Human manual testing preparation

Thirty cases are drafted in `manual-test-cases.csv`; all are NOT RUN. Execute at least
20 with positive/negative workflow, API and permission/security categories. Do not copy
automated test results into Actual result or mark PASS without human execution.

Use a dedicated local PostgreSQL database for rehearsal with the normal README setup.
Do not reset the existing development database or change demo credentials. Provision
separate fixture accounts/project names prefixed `manual.` through the application Admin
screens, privately record initial passwords, and complete each initial password change.
Use Admin, two Managers, two project Employees and an unrelated Employee. Record actual
IDs for direct URL/API checks. Use today's dates, strong private fixture passwords and
no personal data. Deactivate fixture accounts after testing; preserve recorded history.

Run the server, open a 1440×900 desktop browser, and follow CSV steps. For API cases use
`docs/api.md` exact routes and session/CSRF examples; inspect status and response body
with browser developer tools or a manually operated HTTP client. Never publish session
cookies/passwords in evidence. The documented SQL comparison command is read-only.

For each case record actual outcome, PASS/FAIL, evidence filename and any defect. Capture
reproduction, expected/actual result, severity and retest evidence for failures. Exercise
keyboard-only navigation/focus, native browser-menu 200% zoom, table-region scrolling,
and current Firefox/Safari if available. Those human checks remain unexecuted.

Current automated evidence is in `workspace-ui-verification.md` and
`task-ui-verification.md`. Full clean-checkout setup rehearsal and human manual evidence
remain required before calling the assignment submission-ready. No submission/push or
deployment is part of this phase.

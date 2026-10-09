# Local 40-case evidence index

Agent-executed local browser/HTTP checks with isolated PostgreSQL readback.

| Case | Status | Scenario | Event log | Screenshots |
| --- | --- | --- | --- | --- |
| M01 | PASS | Valid sign-in for all three roles | [M01.json](M01.json) | [M01-admin.png](M01-admin.png), [M01-neha.png](M01-neha.png), [M01-asha.png](M01-asha.png), [M01-final.png](M01-final.png) |
| M02 | PASS | Invalid and empty sign-in credentials | [M02.json](M02.json) | [M02-incorrect-credentials.png](M02-incorrect-credentials.png), [M02-final.png](M02-final.png) |
| M03 | PASS | New account password-change gate | [M03.json](M03.json) | [M03-password-errors.png](M03-password-errors.png), [M03-final.png](M03-final.png) |
| M04 | PASS | POST logout and protected-page access | [M04.json](M04.json) | [M04-final.png](M04-final.png) |
| M05 | PASS | Create account and reject duplicate identifier | [M05.json](M05.json) | [M05-final.png](M05-final.png) |
| M06 | PASS | Edit account and explicitly reset password | [M06.json](M06.json) | [M06-final.png](M06-final.png) |
| M07 | PASS | Role changes with dependent relationships | [M07.json](M07.json) | [M07-neha.png](M07-neha.png), [M07-asha.png](M07-asha.png), [M07-final.png](M07-final.png) |
| M08 | PASS | Deactivate account with open session and work history | [M08.json](M08.json) | [M08-final.png](M08-final.png) |
| M09 | PASS | Create project with equal dates and correct owner | [M09.json](M09.json) | [M09-final.png](M09-final.png) |
| M10 | PASS | Invalid project dates and required fields | [M10.json](M10.json) | [M10-dates.png](M10-dates.png), [M10-dates.png](M10-dates.png), [M10-required.png](M10-required.png), [M10-simulated-failed-save.png](M10-simulated-failed-save.png), [M10-final.png](M10-final.png) |
| M11 | PASS | Project edit, persistence and no-results state | [M11.json](M11.json) | [M11-final.png](M11-final.png) |
| M12 | PASS | Project/team/report URL isolation | [M12.json](M12.json) | [M12-arjun-unavailable.png](M12-arjun-unavailable.png), [M12-dev-unavailable.png](M12-dev-unavailable.png), [M12-final.png](M12-final.png) |
| M13 | PASS | Add active Employee and reject ineligible members | [M13.json](M13.json) | [M13-final.png](M13-final.png) |
| M14 | PASS | Reject duplicate project membership | [M14.json](M14.json) | [M14-final.png](M14-final.png) |
| M15 | PASS | Block removal with unfinished assignments | [M15.json](M15.json) | [M15-final.png](M15-final.png) |
| M16 | PASS | Remove member after reassignment | [M16.json](M16.json) | [M16-final.png](M16-final.png) |
| M17 | PASS | Create and assign task through the desktop UI | [M17.json](M17.json) | [M17-final.png](M17-final.png) |
| M18 | PASS | No eligible members, blank title and nonmember selection | [M18.json](M18.json) | [M18-no-eligible-members.png](M18-no-eligible-members.png), [M18-final.png](M18-final.png) |
| M19 | PASS | Edit/reassign task with fixed project | [M19.json](M19.json) | [M19-final.png](M19-final.png) |
| M20 | PASS | Employee starts assigned task | [M20.json](M20.json) | [M20-final.png](M20-final.png) |
| M21 | PASS | Reject skipping, reversing and reopening status | [M21.json](M21.json) | [M21-final.png](M21-final.png) |
| M22 | PASS | Completion confirmation and cancellation | [M22.json](M22.json) | [M22-confirmation.png](M22-confirmation.png), [M22-final.png](M22-final.png) |
| M23 | PASS | Completed-task and time locks | [M23.json](M23.json) | [M23-final.png](M23-final.png) |
| M24 | PASS | Hours/minutes positive and boundary durations | [M24.json](M24.json) | [M24-final.png](M24-final.png) |
| M25 | PASS | Invalid hours/minutes retain useful input | [M25.json](M25.json) | [M25-validation.png](M25-validation.png), [M25-final.png](M25-final.png) |
| M26 | PASS | Reject future work dates | [M26.json](M26.json) | [M26-final.png](M26-final.png) |
| M27 | PASS | Edit time and cancel/confirm deletion | [M27.json](M27.json) | [M27-delete-confirmation.png](M27-delete-confirmation.png), [M27-final.png](M27-final.png) |
| M28 | PASS | Time ownership and task-state permissions | [M28.json](M28.json) | [M28-final.png](M28-final.png) |
| M29 | PASS | Stale time form after completion or reassignment | [M29.json](M29.json) | [M29-completed.png](M29-completed.png), [M29-reassign.png](M29-reassign.png), [M29-final.png](M29-final.png) |
| M30 | PASS | Report totals, completion and empty project | [M30.json](M30.json) | [M30-report.png](M30-report.png), [M30-final.png](M30-final.png) |
| M31 | PASS | Role-scoped Overview and reports | [M31.json](M31.json) | [M31-final.png](M31-final.png) |
| M32 | PASS | Explicit Admin completed-work corrections | [M32.json](M32.json) | [M32-final.png](M32-final.png) |
| M33 | PASS | SQL/report agreement and persistence | [M33.json](M33.json) | [M33-final.png](M33-final.png) |
| M34 | PASS | REST workflow, partial updates and malformed input | [M34.json](M34.json) | [M34-final.png](M34-final.png) |
| M35 | PASS | Forged ownership and privileged fields | [M35.json](M35.json) | [M35-final.png](M35-final.png) |
| M36 | PASS | List/filter/detail/report privacy and picker scope | [M36.json](M36.json) | [M36-final.png](M36-final.png) |
| M37 | PASS | CSRF and strict JSON minutes | [M37.json](M37.json) | [M37-final.png](M37-final.png) |
| M38 | PASS | Stored XSS, search input and account permissions | [M38.json](M38.json) | [M38-final.png](M38-final.png) |
| M39 | PASS | Overview visibility before and after Employee starts a task | [M39.json](M39.json) | [M39-neha-before-start.png](M39-neha-before-start.png), [M39-admin-before-start.png](M39-admin-before-start.png), [M39-neha-after-start.png](M39-neha-after-start.png), [M39-admin-after-start.png](M39-admin-after-start.png), [M39-final.png](M39-final.png) |
| M40 | PASS | Protect history and allow safe deletion | [M40.json](M40.json) | [M40-final.png](M40-final.png) |

M10 failed-save is a controlled test-only simulation. M39 verifies Overview visibility after Employee Start task.

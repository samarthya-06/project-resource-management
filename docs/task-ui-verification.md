# Phase 4B — task/time desktop workflow verification

Executed 8 October 2026 in the existing worktree. Phase 4A changes were already
present and uncommitted; preserved them and all existing backend behavior. Mutation
checks used isolated PostgreSQL test fixtures, with no development record or demo
password changes. No migrations, service rules, authentication behavior, API resources,
report formulas, SQL or dependencies were rewritten. No push/deployment/reset occurred.

## Implemented workflow and permissions

- Project Tasks: status/assignee filters, 25-row ID ordering, empty/no-results states,
  real counts/time and task-detail links. Read filters include current members and
  historical assignees; unrelated users cannot appear in picker results.
- Create/edit/reassign share TaskForm. Project is fixed; new assignments select active
  Employee members. Blank edit assignment retains the current historical/inactive
  assignee. Empty eligible-member guidance links to Team. Admin/owning Manager only.
- Employee My tasks: current assignments within membership scope, status/project filters,
  default unfinished, real status totals and original own logged time. Overview links
  and project Tasks navigation are connected; no placeholder actions remain.
- TODO/In progress/Completed task details with readable date/duration/history, description,
  current assignee and progress. Managers/Admin have management variants; unrelated team
  Employees can read summaries but have no task/time management controls.
- POST Start task and confirmed completion use existing forward-transition rules.
  Confirmation explains recording remaining time first and subsequent read-only locks.
  Repeated same-status completion POST remains a no-op under the existing contract.
- Own time creation/editing share TimeForm. Date/minutes/note only; contributor comes from
  the actor. Whole minutes 1–1440 and no future dates reuse existing model validation.
  Edit/delete require own entry, current assignment/membership and IN_PROGRESS.
  Deletion requires a confirmation checkbox. Managers cannot edit employee time.
- Completed tasks hide ordinary edits/reassignment/deletion/time actions and show a
  read-only explanation. Admin uses explicit task/time correction forms with retained
  COMPLETED status and original task/contributor identity; no correction subsystem added.
- Safe unfinished task deletion is confirmed and uses the existing service. Recorded
  history rejects deletion through a controlled error rather than a server failure.

Pages recheck active authenticated actors and password gating. Selectors scope reads
before filtering/pagination; Employee history queries include only their own entries
and notes. Existing services authorize every write and reread fresh task state inside
existing transactions/locks. Forms whitelist fields and parse input without saving
models or duplicating domain rules in JavaScript. No new locking architecture was added.

GET never changes state. Every mutation requires POST/CSRF; unsupported methods return
405. Foreign/missing records return 404. Forbidden role/read URLs return 403. Validated
HTML form errors/database-save failure retain values with 200; invalid list filters
return 400. Fresh service permission rejection retains entered values with a 403 and
completion/reassignment guidance. Failed inline time saves reuse the full-page Log
time form. Shared JavaScript supplies Saving…/disabled-submit and error-summary focus.

## Actual automated checks

Commands ran with `uv run --cache-dir .cache/uv`, the existing PostgreSQL configuration,
and installed Chromium. No SQLite substitution. Browser fixtures seed only the test
database and serve Django/static files on an ephemeral local port.

| Check | Actual result |
| --- | --- |
| Focused Phase 4A HTML regression | 18 passed in 3.52 seconds |
| Final focused task/time HTML tests | 22 passed in 3.67 seconds |
| Task/time Chromium journeys after locator fixes | 3 passed in 19.64 seconds |
| First combined full PostgreSQL suite | 270 passed in 74.88 seconds, no warnings |
| Final full PostgreSQL suite after final review changes | **270 passed in 75.48 seconds, no warnings** |
| `python manage.py check` | No issues (0 silenced) |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `ruff check accounts config projects tests scripts` | All checks passed |
| `ruff format --check accounts config projects tests scripts` | 61 files already formatted |
| `git diff --check` | Passed |
| Read-only SQL/application report comparison on development data | MATCH: 4 projects, 4 contributor groups |

SQL comparison: Website 6 tasks/2 completed/720 minutes; Onboarding 5/2/720;
Knowledge Base 0/0/0; Operations 1/0/0. No reseeding or resetting development data.
The full suite preserves the existing 224 backend/authentication/API/report/SQL tests,
the Phase 4A 18 HTML checks and 3 journeys, and adds 22 HTML checks and 3 journeys.

HTML coverage includes the complete create/start/time/edit/complete journey, foreign
Manager/unrelated Employee URLs, team private-note isolation, scoped/default filters,
protected-field forgery, member-selection guidance, invalid/future time, confirmed
deletion/protected history, completed locks and retained stale input, reassignment,
Admin correction/attribution, historical assignee retention, simulated database failure,
real CSRF, pagination/filter retention and initial-password/inactive session gates.

Browser journeys exercise real login and forms: Manager creates a project, adds Dev,
creates/edits an assigned task; Employee starts it, logs 90 minutes, edits to 120, sees
a retained-note fraction error, creates/deletes an extra entry, confirms completion and
gets a 403 for a later edit. Manager sees 120 minutes/2h in Report and cannot edit the
completed task. Admin reassigns a completed task and corrects 240 to 250 minutes while
retaining Asha as original contributor and COMPLETED. Foreign Manager/unrelated Employee
receive 404; the new assignee cannot see Asha's note/history, and Asha can read her own.
Separate seed journeys check status/assignee/project filters and empty member guidance.

At 1440×900, browser assertions check the 48px header, 240px sidebar, no page-wide
horizontal overflow, no dummy links and right-aligned numeric cells. Keyboard checks
cover Tab between task fields and visible outline; errors receive summary focus. Existing
Phase 4A journeys also cover skip-link/main focus and account/project form operation.
200% equivalent reflow uses 720×450 CSS pixels at DPR 2: task/time actions remain reachable,
the time form/history stack, and tables scroll inside a focusable region rather than
expanding the whole page. This is automated reflow evidence, not native browser-menu
zoom or a human manual test. Screen-reader/other-browser/native-zoom review remains.

## Paper comparison and evidence

Inspected the live editable [Paper canvas](https://app.paper.design/file/01M4BSRQY350PXSN06W3J5RHJR/p-1-0)
after the user reopened Paper Desktop. Initially the connection reported Desktop not
running; the subsequent guide/basic-info/JSX/style/screenshot calls succeeded. No current
Paper blocker. Read Project Tasks/Create task/My tasks/In progress JSX, computed shell
styles and live TODO/In progress/Completed/Project Tasks screenshots. Supplied PNGs remain
additional references; no design edit was necessary.

Compared rendered screenshots against Paper. Review verdict: consistent 32px page padding,
24px rhythm, 384px Log time panel, clear IBM Plex hierarchy, readable contrast and aligned
semantic table columns. Content scrolls vertically where real forms add height; no fixed
artboard clipping is applied to application pages. The zoom table region deliberately
scrolls horizontally, and its controls remain keyboard reachable. No exact pixel-parity
claim or complete accessibility-conformance claim.

Differences: IBM Plex replaces incidental system-font layers; native controls, persistent
filter labels/submit actions, multiline notes, right-aligned durations, actual descriptions
and seed entries/dates, message banners, checkbox confirmations and explicit contributor/
correction guidance. Completed tasks retain descriptions where present. My tasks is
Employee-only; Manager/Admin manage work through Projects. These reuse Phase 4A patterns.

Twenty-two screenshots are in `docs/evidence/tasks/`, including:

| Screen/state | Evidence |
| --- | --- |
| Project Tasks / Create / Edit | [tasks](evidence/tasks/manager-project-tasks.png), [create](evidence/tasks/manager-create-task.png), [edit](evidence/tasks/manager-edit-task.png) |
| My tasks / TODO / In progress | [My tasks](evidence/tasks/employee-seed-my-tasks.png), [TODO](evidence/tasks/employee-todo.png), [In progress](evidence/tasks/employee-seed-in-progress.png) |
| Time edit / invalid duration / delete confirmation | [edit](evidence/tasks/employee-edit-time.png), [invalid](evidence/tasks/employee-time-validation.png), [delete](evidence/tasks/employee-delete-time-confirmation.png) |
| Completion / read-only / Manager report | [confirm](evidence/tasks/employee-completion-confirmation.png), [completed](evidence/tasks/employee-completed.png), [report](evidence/tasks/manager-workflow-report.png) |
| Admin correction forms | [task](evidence/tasks/admin-task-correction.png), [time](evidence/tasks/admin-time-correction.png) |
| Empty team / 200% equivalent reflow | [no members](evidence/tasks/manager-no-eligible-member.png), [zoom](evidence/tasks/employee-time-200-percent.png) |

## Issues found and fixes

- Early browser shell assertion counted both sidebar and breadcrumb My tasks links;
  scoped the navigation assertion to sidebar. A sign-out locator on Django's debug 404
  lacked a shell; returned to Overview first. Three complete journeys then passed.
- A retained-input assertion expected Python integer 60 rather than submitted HTML string
  "60"; corrected the test to verify the transport value. Production behavior was correct.
- Final review added filter options for project members without tasks (alongside historical
  assignees), and kept available descriptions readable after completion. No service,
  privacy or report rule changed. Final combined regression rerun is recorded below.

## Changed files and human testing readiness

- `projects/task_views.py`: task/time HTML adapters and shared scoped list context.
- `projects/forms.py`, `projects/display.py`, `projects/ui_helpers.py`, `projects/urls.py`:
  task/time/filter forms, scoped displayed durations, protected-deletion mapping and routes.
- `templates/workspace/`: new task_table/task_filters/project_tasks/my_tasks/task_form/
  task_detail/time_fields/time_form; shared base/project_detail/overview/confirmation/
  pagination connect navigation, links and confirmations.
- `static/css/workspace.css`: task progress/actions/time split, numeric columns and reflow.
  Existing minimal JavaScript is reused without new domain logic.
- `tests/test_task_html.py`, `tests/test_task_browser.py`; existing workspace HTML/browser
  navigation assertions updated for the now-working links. Screenshots in `docs/evidence/tasks/`.
- README, business rules, handoff, implementation plan, Phase 4A verification and known
  limitations updated; `docs/manual-test-cases.csv` and `docs/manual-testing-guide.md` prepared.

No known unresolved functional defect from executed checks. All essential assignment
workflows now have application screens outside Django Admin. Thirty human cases are
drafted, all NOT RUN; at least 20 must be executed with real actual outcomes and evidence.
Native zoom/other-browser/screen-reader checks and clean-checkout setup rehearsal remain.
Automated screenshots/journeys must not be relabelled human manual evidence. The desktop
workflow is ready for that required testing, not yet a completed submission claim.

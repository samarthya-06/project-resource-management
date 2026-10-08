# Phase 4A — desktop workspace verification

Executed 7–8 October 2026 in the existing worktree, starting from `60e20aa`
(Phase 3 on current main). Existing development work and demo credentials were
preserved. UI mutations ran only against isolated PostgreSQL test fixtures.

## Implemented screens and permission path

- Shared desktop shell: 48px charcoal header, 240px sidebar at 1440px, bundled
  IBM Plex Sans, blue actions, square fields/buttons, role navigation and POST logout.
- Admin, Manager and Employee Overview use existing scoped reports plus a small
  display helper. Admin includes every project and active/inactive Employee accounts;
  Manager includes owned projects; Employee counts current own assignments and original
  time contributions in membership projects. Up to ten relevant task summaries appear.
- Admin Employees supports name/login search, active/inactive filter, account creation,
  editing, optional password reset and confirmed deactivation. No Activate action.
  Role changes require confirmation and the existing reassignment guards. Privilege
  flags are unavailable; new/reset passwords restore the initial-password requirement.
- Projects supports scoped name search, 25-row pagination, create/edit, readable dates,
  zero-task projects and current counts/durations. Admin chooses a Manager; Managers
  have fixed actor ownership. Project Overview/Team/Report enforce the same scope.
- Team add offers active Employees not already on the team. Removal is a full-page
  confirmation and rejects unfinished assignments. History explanations accompany
  removal and deactivation. Employee project screens have no management actions.
- Employee reports say Own work and contain no other Employee's detailed time notes.
- Shared fields, semantic tables/captions, messages, error summaries/inline errors,
  saving feedback, empty/no-results and generic denied/unavailable pages. Nonsecret
  form values survive failures; passwords do not echo. Password change retains the
  centered authentication layout and adds consistent error/saving handling.

Every page reloads the active authenticated actor. Selectors scope reads before
search/pagination; services authorize and validate every mutation using their existing
transactions/locks. Forms whitelist inputs and parse transport values; they do not
save models or replace business rules. GET displays confirmation only; POST with
CSRF performs a write. Foreign/missing project records return 404; authenticated
forbidden role actions return 403. Django's debug-off error pages disclose no resource
names. The Django server never calls its own HTTP API.

No model, applied migration, authentication operation, seed implementation, service,
resource API, report calculation or SQL file was changed. All existing 224 tests remain.
No push, deployment, development database reset or migration rewrite occurred.

## Actual checks

Commands ran with `uv run --cache-dir .cache/uv` and the configured PostgreSQL backend.
Chromium was already installed; browser fixtures served static assets on a local
live-server port. No SQLite substitute or development-database mutation was used.

| Check | Result |
| --- | --- |
| Full `pytest -q --tb=short` | **245 passed in 54.68 seconds**, no warnings |
| Existing tests within full run | **224 passed**, including authentication, business rules, API/report and SQL comparisons |
| New tests within full run | **18 HTML tests and 3 Chromium journeys passed** |
| Final HTML/browser run after spacing polish | **21 passed in 17.86 seconds**, no warnings |
| `python manage.py check` | No issues (0 silenced) |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `ruff check accounts config projects tests scripts` | All checks passed |
| `ruff format --check accounts config projects tests scripts` | 58 files already formatted |
| `git diff --check` | Passed |

HTML coverage: real role metrics/navigation; scoped searches/direct URLs; Admin-only
account pages/actions; project manager derivation/selection/change; reversed dates;
forged ownership and protected fields; account create/edit/reset/deactivate/history;
password non-echo; role confirmation and invalid role-change guards; duplicate/nonemployee
members and unfinished removal; nonmutating GET; simulated database-save failure with
retained input; readable durations/empty projects; real CSRF rejection and unsupported methods.

Chromium journeys use real login and server-rendered forms. Admin creates, edits and
deactivates a fixture account, checks no-results, and sees the project Manager selector.
Manager creates/edits a fixture project, gets a retained-input date error, adds/removes
an eligible member, and receives an unfinished-task removal rejection. An authorized
Employee views read-only project sections and Own work reports; unrelated Employee and
foreign Manager direct project access return 404. Nothing modifies development fixtures.

Keyboard assertions exercise the skip link, main-content focus, Tab between fields,
visible input outline and keyboard-entered values. Error summaries receive focus.
At 1440×900 the header/sidebar dimensions and absence of whole-page horizontal overflow
are asserted, along with right-aligned numeric columns and absence of placeholder links.

200% zoom-equivalent reflow uses a 720×450 CSS viewport at device scale factor 2 (the
same physical width as 1440×900), inspecting the project report and edit form. Tiles and
fields stack, actions remain reachable, and there is no whole-page horizontal overflow.
This is automated reflow evidence, not a native browser-menu zoom or human manual test.

A script calculated selected color-pair contrast using relative luminance: body/white
18.10:1, helper/field 7.10:1, primary button 5.00:1, error/error surface 4.55:1,
blue focus/field 4.55:1, input border/field 3.02:1, completed tag 7.00:1 and progress
tag 5.94:1. This checks those pairs, not complete WCAG or screen-reader conformance.

## Paper comparison and evidence

Editable canvas: [project-resource-management](https://app.paper.design/file/01M4BSRQY350PXSN06W3J5RHJR/p-1-0).
The earlier linked copy briefly lacked account edit access; the new editable copy
resolved that blocker. Paper screenshots, exact JSX/styles and tree structure were
inspected, including the current Manager Overview and corrected project Report.
The user's eighteen 2880×1800 PNG exports also served as visual references.

Compared rendered screenshots with the corresponding Paper/PNG composition. Header,
sidebar, page padding, metric strip, panels, field widths and table pattern follow the
reference. Final spacing polish aligns metric height, navigation rows and task-column
proportions. Numeric columns were corrected in the Phase 4A Paper artboards too.
The reference now removes activation guidance/actions and uses private password-handoff
copy. No access blocker remains, and working indicators were released.

There is **no exact pixel-parity claim**. Documented differences:

- IBM Plex Sans is applied consistently, replacing incidental system-font layers.
- Real values/names replace samples: Admin sees four seeded projects and four Employee
  accounts; Employee Overview shows all four own unfinished tasks rather than three
  illustrative rows. Completion uses the real rounded percentage (33.33%, not 33%).
- Working project links replace task links pending Phase 4B. My tasks and Tasks section
  navigation are omitted until implemented; Change password is reachable in the sidebar.
- Persistent search labels/submit buttons, native select/date controls, larger multiline
  description fields, optional contact email and error-summary focus alter form dimensions.
  Names are optional to match existing account service contracts.
- Team shows activity status instead of login identifiers and renders names as text;
  contributor names are text because no profile-detail screen is implemented.
- Removal/deactivation use full-page confirmation with an explicit checkbox. Employee
  reports add an Own work banner. Zero-task reports show 0% and No tasks yet.
- Accessible link underlines and status labels supplement the reference styling.

Twenty-four generated screenshots are saved in `docs/evidence/workspace/`. Examples:

| Screen/state | Evidence |
| --- | --- |
| Admin Overview | [admin-overview.png](evidence/workspace/admin-overview.png) |
| Admin account list / no results | [list](evidence/workspace/admin-employees.png), [no results](evidence/workspace/admin-no-results.png) |
| Create/edit/deactivate account | [create](evidence/workspace/admin-create-employee.png), [edit](evidence/workspace/admin-edit-employee.png), [confirmation](evidence/workspace/admin-deactivate-confirmation.png) |
| Manager Overview / Projects | [Overview](evidence/workspace/manager-overview.png), [Projects](evidence/workspace/manager-projects.png) |
| Project validation / edit | [validation](evidence/workspace/manager-project-validation.png), [edit](evidence/workspace/manager-edit-project.png) |
| Project Overview / Team / Report | [Overview](evidence/workspace/manager-project-overview.png), [Team](evidence/workspace/manager-project-team.png), [Report](evidence/workspace/manager-project-report.png) |
| Add member / blocked removal | [add](evidence/workspace/manager-add-member.png), [blocked removal](evidence/workspace/manager-member-removal-blocked.png) |
| Zero-work report | [empty report](evidence/workspace/manager-empty-report.png) |
| Employee Overview / Own work / unavailable | [Overview](evidence/workspace/employee-overview.png), [Own work](evidence/workspace/employee-project-report.png), [unavailable](evidence/workspace/employee-unavailable.png) |
| Password change | [password-change.png](evidence/workspace/password-change.png) |
| Zoom-equivalent report / form | [report](evidence/workspace/manager-report-200-percent.png), [form](evidence/workspace/manager-project-form-200-percent.png) |

These images and automated journeys are not human manual-case PASS evidence.

## Discovered issues and corrections

- Initial browser fixture initialization conflicted with Playwright's synchronous
  driver event loop and Django's async guard. Localized the driver/environment to the
  test fixture. A subsequent PostgreSQL teardown warning exposed a connection opened
  in that loop context; closing it before exiting the driver resolved the warning.
  Production settings/guards are unchanged. Final runs passed without warnings.
- Two early browser assertions mishandled whitespace/required-label text. Corrected
  the locators/assertions; all three complete journeys now execute.
- Zero-task completion initially displayed only No tasks yet; corrected it to show
  0% alongside that label and added a browser assertion.
- The eligible-member form initially included current members. It now excludes them;
  the shared duplicate guard still rejects forged requests.

## Changed files and next milestone

- Routing: `config/urls.py`, `accounts/urls.py`, new `projects/urls.py`.
- HTML adapters/forms/display: `accounts/workspace_forms.py`, `accounts/workspace_views.py`,
  `projects/views.py`, `projects/forms.py`, `projects/display.py`, `projects/ui_helpers.py`,
  `projects/templatetags/__init__.py`, `projects/templatetags/workspace.py`.
- Templates: `templates/workspace/` shell/partials/pages; `templates/403.html`,
  `templates/404.html`, `templates/base.html`, `templates/accounts/password_change.html`.
- Styling/interaction: `static/css/workspace.css`, `static/js/workspace.js`.
- Tests/evidence: `tests/test_workspace_html.py`, `tests/test_workspace_browser.py`,
  `docs/evidence/workspace/*.png`.
- Documentation: `README.md`, `docs/business-rules.md`, `docs/api-verification.md`,
  `docs/implementation-plan.md`, `docs/paper-ui-handoff.md`, `docs/known-limitations.md`,
  this verification record.

Phase 4B: project task list/create/edit/assignment, My tasks, task details/status/time
forms, completion confirmation/locks and explicit Admin correction screens. Existing
backend/API operations are ready to reuse. Required human manual cases, native zoom,
other-browser/screen-reader checks and clean-checkout submission rehearsal remain.
Mobile artifacts are excluded by the user. No further Phase 4A infrastructure blocker.


## Subsequent Phase 4B update

The missing task/time screens and navigation listed above are now implemented; this
record remains the historical Phase 4A result. Overview titles now link to task details,
Employees have My tasks navigation, and projects have the Tasks tab. Existing browser
navigation assertions were updated to check the implemented role navigation. See
`task-ui-verification.md` for the current combined regression results and screenshots.

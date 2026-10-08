# Paper UI design handoff

Design session: 7 October 2026.
Current editable canvas: https://app.paper.design/file/01M4BSRQY350PXSN06W3J5RHJR/p-1-0
Previous account copy: https://app.paper.design/file/01M4B6HF35VC0BWDT7VKCV7YMY/p-1-0
Previous copy: https://app.paper.design/file/01M4B5SPHF2QH0BVJFMJZEE4PF/p-1-0
Original canvas: https://app.paper.design/file/01M4B48N247NKY6049SS6QAMA4/p-1-0

## Direction

Use `design.md` as the application contract and `docs/DESIGN-ibm.md` as visual inspiration. The requested `gpt-taste` skill informs spacing, hierarchy, contrast and visual review; its marketing-page structures, alternate fonts, React and cinematic-motion defaults do not override the assignment's Django application design.

The desktop designs use 1440 × 900 artboards, a 48px charcoal header, a 240px white sidebar, IBM Plex Sans, square controls, neutral surfaces, primary blue #0f62fe and compact aligned tables. Design tokens are saved in Paper. Some explicit reference values remain in layers; normalize them to shared tokens during implementation.

## Actual progress

| Artboard | Status |
| --- | --- |
| Manager · Projects | Designed and screenshot-reviewed |
| Manager · Overview | Designed and screenshot-reviewed; active navigation corrected and rechecked |
| Manager · Project team | Designed and screenshot-reviewed; membership-removal rejection shown |
| Manager · Project tasks | Designed and screenshot-reviewed; all three status types shown |
| Manager · Project report | Designed and screenshot-reviewed; contributor attribution and scope explained |
| Employee · My tasks | Completed and screenshot-reviewed; title and Employee identity corrected |
| Employee · Task in progress | Completed and screenshot-reviewed; time form/history and completion guidance |
| Employee · Completed task | Completed and screenshot-reviewed; read-only banner and historical time |
| Admin · Employees | Completed and screenshot-reviewed; active/inactive account actions |
| Manager · Create project | Completed and screenshot-reviewed; reversed-date validation example |
| Manager · Create task | Completed and screenshot-reviewed; fixed project and member-only assignment |
| Admin · Create employee | Completed and screenshot-reviewed; duplicate-identifier validation example |
| Login | Completed and screenshot-reviewed; generic credentials error |
| Employee · Task to do | Completed and screenshot-reviewed; Start task and time-entry restriction |
| Manager · Project overview | Completed and screenshot-reviewed; description, team and task breakdown |
| Desktop · Confirmations and feedback | Completed and screenshot-reviewed; completion, deactivation, failed save, stale state, empty and unavailable examples |
| Manager · Add project member | Completed and screenshot-reviewed; active eligible employee picker and duplicate/empty guidance |
| Employee · Overview | Completed and screenshot-reviewed; own task statuses and own hours |
| Admin · Overview | Completed and screenshot-reviewed; all-workspace metrics and Employees navigation |

Nineteen desktop artboards persist in the current canvas (1138 nodes and nine tokens, inspected at session end). The user explicitly excluded mobile layouts; the two mobile drafts were removed. No mobile or tablet design artifacts are planned.

## Sample-data contract

The sample manager is Neha Sharma. Client Website Redesign runs from 06–23 October 2026 and has six tasks, two completed, four unfinished and twelve recorded hours. Its contributors are Asha Deshmukh (420 minutes / 7h) and Ravi Kulkarni (300 minutes / 5h).

| Task | Employee | Status | Hours |
| --- | --- | --- | --- |
| Design homepage layout | Asha | IN_PROGRESS | 3 |
| Implement navigation | Ravi | IN_PROGRESS | 2 |
| Review page content | Asha | TODO | 0 |
| Test mobile navigation | Ravi | TODO | 0 |
| Audit existing website | Asha | COMPLETED | 4 |
| Define content structure | Ravi | COMPLETED | 3 |

Employee Onboarding Portal has five tasks, two completed and twelve hours. Internal Knowledge Base has zero tasks and zero hours. Manager aggregate values are three projects, seven unfinished tasks, four completed tasks and twenty-four hours. These are illustrative design values, not database or report-test evidence.

## Session continuity

Two earlier accounts reached Paper's weekly MCP allowance. The user switched accounts and opened another copy. Existing work was retained, tokens restored and desktop design continued. No quota error occurred at the end of this session; all working indicators were released.

## Remaining design coverage

- Project, task and employee edit variants; role-change confirmation and explicit Admin correction of completed work.
- Invalid-duration, missing-member, stale-assignment, loading and saving states where not already shown.
- Consistent numeric-column alignment and user-facing password helper guidance.

Mobile layouts are excluded by the user's latest instruction. These remaining variants can reuse the established forms and state patterns, but have not been separately designed or verified.

## Verification and implementation limits

Visual reviews checked desktop spacing, readable type, table alignment and artboard fit for the desktop compositions across the sessions. The new desktop additions were screenshot-reviewed in the current account. An extra spacing placeholder in the time-entry area was removed and the correction screenshot-reviewed. Numeric columns still need consistent right alignment during final polish. The Manager Overview's corrected navigation was screenshot-checked. Formal contrast calculations, keyboard behavior, mobile layouts and browser testing have not been completed. The account password helper should be revised to user-facing guidance during implementation rather than describing password hashing.

These are editable visual designs. Buttons do not yet execute workflows; there is no application/backend implementation from this session. When converting, read exact Paper structure/styles with its code and style tools, translate to shared Django partials and CSS, then verify browser renderings. Add semantic table markup, accessible labels/focus, CSRF/session handling and backend permissions rather than treating visual restrictions as authorization.

## Authentication implementation update

The Django foundation and working login/password-change/logout are now implemented. Login dimensions were read through Paper export; IBM Plex Sans follows the application specification. See `auth-foundation-verification.md` for executed PostgreSQL and desktop browser checks. The remaining Paper application screens are still designs awaiting implementation.

## Phase 4A implementation update — 7–8 October 2026

The current editable copy is named `project-resource-management`; all 19 desktop
artboards and 1138 nodes were inspected through Paper. This copied file reports zero
saved tokens, while the previous copy has nine; shared CSS tokens implement the
specified colors/font in the application. The user also supplied eighteen @2x PNGs.
Paper screenshots/styles and those PNGs served as comparison references.

Corrected the editable reference: inactive Employees actions now say Edit, initial
password help says “Share privately. Password change is required.”, member-picker
empty guidance no longer suggests activation, and Phase 4A project/Overview/team/report
numeric columns are right-aligned. Report alignment was screenshot-rechecked. The
supplied PNGs predate these corrections and remain historical visual references.

Implemented shared desktop UI, three role Overviews, Employees, Projects/create/edit,
project Overview/Team/Report and member add/remove. Edit variants reuse form patterns.
The app adds persistent search labels, native controls, accessible error summaries,
private password-handoff guidance and explicit POST confirmations. Task/time pages
and correction screens remain Phase 4B; their design navigation is intentionally not
exposed in the app yet. See `workspace-ui-verification.md` for screenshot comparisons,
executed browser/PostgreSQL checks and the limits of visual parity/accessibility evidence.


## Phase 4B implementation comparison — 8 October 2026

User-requested duration improvement (8 October): Log time, Edit time and Admin
correction now use Hours and additional Minutes (0–59). The server converts them
to whole minutes; the stored schema and REST contract are unchanged. This deliberately
differs from the supplied Paper exports' single Minutes input and reuses the existing
two-column field grid, labels, helper text and validation styles.

Paper Desktop was initially unavailable, then reopened by the user. The current editable
file above was successfully inspected (19 artboards, 1138 nodes, zero saved tokens in
this account copy). Read live JSX for Project Tasks/Create task/My tasks/In progress,
computed header/sidebar/content styles, and live screenshots of TODO/In progress/
Completed/Project Tasks. The app retains the established Phase 4A tokens rather than
creating another system. Log time uses the exact 384px panel, 24px gap, 48px controls and
shared neutral/blue surfaces. Screenshot review covered spacing, type, contrast,
alignment and overflow; no Paper mutations were needed.

Task navigation and dashboard links now work. Manager/Admin details, edit/reassignment,
time editing/deletion and Admin corrections reuse the supplied forms and confirmations.
Differences: persistent labels and Apply/Clear filter controls; native date/select/number
inputs; multiline notes; actual dates/descriptions/time entries instead of samples;
right-aligned duration columns; explicit original-contributor names for Manager/Admin;
full-page checkbox confirmations; extra read-only description where present. These
changes make states/permissions usable and do not claim exact pixel parity. My tasks is
Employee-only, matching backend role responsibilities. See `task-ui-verification.md`.

# Project & Resource Management System — Design specification

Status: proposed implementation baseline, 7 October 2026.
Design scope update: the user requested desktop-only Paper designs; mobile and tablet layout artifacts are excluded from this design pass. Earlier narrow-screen guidance remains an implementation consideration, not a requirement to create mobile mockups.
Audience: UI designer, Google Stitch, and development assistant.
Stack: Django, Django REST Framework, PostgreSQL, HTML/CSS/JavaScript.

## 1. Design foundation and precedence

Use the uploaded DESIGN-ibm.md as the visual foundation. Its contents match the reference at https://getdesign.md/design-md/ibm/DESIGN.md, linked from https://getdesign.md/ibm/design-md.
This is an original application specification informed by that reference, not an unchanged copy or an official IBM product.

Retain the reference's neutral surfaces, restrained blue accent, IBM Plex Sans, square components, subtle dividers and orderly spacing. Adapt its marketing layout to a daily work application. Omit hero sections, promotional banners, photography, customer logos and marketing footers. Use compact application typography instead of large display headings.

Official supporting references:
- https://www.carbondesignsystem.com/building-blocks/foundations/color/tokens
- https://www.carbondesignsystem.com/building-blocks/foundations/typography/type-sets

Priority: assignment business rules > accessible operation > this product specification > marketing-reference suggestions.
The measurements below are project choices; they do not imply complete Carbon conformance.
Do not use IBM branding or claim affiliation. Product name: Project & Resource Management System; abbreviated shell label: Project Workspace.

### Review of the supplied reference

- It explicitly covers enterprise marketing and acknowledges missing product components. It needs application-specific tables, permissions, workflow states and time-entry forms.
- Its token named blue-60 is #0043ce while primary is #0f62fe. Avoid propagating confusing palette names; use semantic primary/hover/pressed names in our app.
- Radius guidance varies between the description, token inventory and strict square-corner rules. Our decision is 0px for panels, fields and buttons; 2px is allowed only for compact status tags.
- Focus instructions vary between charcoal underline, blue underline and outline. Our app uses a persistent 2px blue focus outline with a 2px offset; inverse surfaces also need a contrasting inner outline. Error styling must not obscure keyboard focus.
- Muted #8c8c8c text is not suitable for essential small text on white. Use #525252 for helper text and captions; reserve lighter gray for disabled content.
- The reference suggests an external lint command. Do not assume that command is available or required; the acceptance checklist below governs this project.

## 2. Product goal and scope

Help managers answer: What work exists, who owns it, how far has it progressed, and how much time has been recorded?
Help employees answer: What am I assigned, what should I do next, and where do I record work?

Required capabilities: employee management, project management, project membership, task management and assignment, task status, project start/end dates, time tracking, basic reports, REST APIs and role-based access.
Task values are exactly TODO, IN_PROGRESS and COMPLETED. Display labels: To do, In progress, Completed.
Do not imply functionality for billing, chat, AI assistance, notifications, Gantt planning, resource forecasting or live timers. Table-first task management is the baseline. A board is optional only after required functionality is verified.

## 3. Visual tokens

Use these project-scoped CSS variables rather than claiming they are the official Carbon API:

```css
:root {
  --app-background: #f4f4f4;
  --app-surface: #ffffff;
  --app-field: #f4f4f4;
  --app-text: #161616;
  --app-text-secondary: #525252;
  --app-border: #e0e0e0;
  --app-border-input: #8d8d8d;
  --app-primary: #0f62fe;
  --app-primary-hover: #0050e6;
  --app-primary-pressed: #002d9c;
  --app-danger: #da1e28;
  --app-focus: #0f62fe;
  --app-shell: #161616;
  --app-shell-text: #ffffff;
  --app-font: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --app-radius: 0px;
}
```

Blue indicates an action, selection or focus. Red indicates errors and destructive actions. Green indicates completion; yellow indicates warnings. Use semantic colour with explicit text, never alone.
Default theme: light work area with a charcoal header and white sidebar. Full dark mode is outside the baseline.
Use borders and surface differences for hierarchy; avoid decorative gradients and card shadows. A modal uses a dimmed backdrop.
Spacing steps: 4, 8, 12, 16, 24, 32 and 48px. Desktop page padding: 32px; tablet: 24px; mobile: 16px.

| Typography role | Size / line height | Weight |
| --- | --- | --- |
| Page heading | 28 / 36px | 400 |
| Section heading | 20 / 28px | 400 |
| Metric value | 32 / 40px | 400 |
| Form content | 16 / 24px | 400 |
| Table and navigation | 14 / 20px | 400 |
| Table heading and emphasis | 14 / 20px | 600 |
| Supporting metadata | 12 / 16px | 400 |

Use sentence case. Keep instructions and validation at least 14px. Numeric columns use tabular figures. Bundle fonts with their license during implementation so the demo does not depend on a font CDN.

## 4. Layout and navigation

Desktop shell: 48px header, 240px sidebar, flexible main content. Header shows product name, signed-in name, role and account/logout menu. Avoid ornamental search or notification buttons.
Sidebar: Overview, Projects, My tasks; Employees for Admin only. Project reporting lives inside project details. Time entries live inside task details; a separate timesheet is not required.
Active navigation has a blue marker, contrasting surface and aria-current. Use breadcrumb links on nested pages. Every page has a title, brief context and a clear primary action when authorized.
Below 1056px the sidebar becomes a menu drawer. Below 672px forms and summary tiles stack. Tables scroll within their own container; keep task/project title identifiable. Touch controls are at least 48px high. Check 1440, 1024, 768, 390 and 320px widths.

## 5. Role-aware experience

These detailed role decisions are proposals based on the assignment and must be documented in the README.

| Capability | Admin | Project Manager | Employee |
| --- | --- | --- | --- |
| Employee accounts | Manage | No account management | Own account display |
| Projects | All | Own projects | Membership projects |
| Project membership | Manage all | Manage own projects | Read assigned team |
| Task creation and assignment | All | Own projects | No |
| Task updates | All | Own projects | Assigned tasks only |
| Project reports | All | Own projects | Own work summary |

Employees must not see foreign-project data in lists, filters, search, reports or direct URLs. Do not disclose foreign resource names in denied states. UI restrictions supplement server authorization.
Treat Employees and Managers as normal users: completed tasks are read-only for them. Admin correction is an explicit exception, with a warning that editing does not silently reopen the task.
Baseline employee editing is limited to status and own time entries. Managers control task description and assignment. Any broader employee editing must be a deliberate documented decision.

## 6. Screen specifications

### Login
Centered form with product title, login identifier, password, show/hide password and Sign in. On failure show a generic credentials message. Preserve the login identifier; never echo the password. Only show demo credentials if explicitly enabled for the demonstration environment.

### Overview
Role-appropriate summary tiles plus a useful task/project table. Admin: employee count, project count, unfinished task count and total logged hours. Manager: own project count, unfinished/completed task counts and project hours. Employee: own To do, In progress, Completed counts and own logged hours.
Label scope and period accurately. All-time totals must say Total logged hours, not Hours this week. Completion does not represent employee utilization or productivity.

### Employees — Admin
Searchable table: name, login identifier, role, active status, actions. Provide create and edit forms, and confirm deactivation. Explain that deactivation preserves work history. Show validation for duplicate identifier and required fields. Role changes require explicit confirmation; do not casually expose elevation to Admin.

### Projects
Table: project name, manager, start date, end date, completed/total tasks and logged hours. Search by name; managers and employees see only allowed records. New project form: name, description, start date and end date. Admin can select manager; manager identity is fixed for a manager creating their own project.
Use task completion terminology rather than inventing a project-status field. Do not add project deadlines to tasks automatically.

### Project details
Heading with name, manager, dates and permitted edit action. Tabs: Overview, Team, Tasks, Report.
- Overview: description, task breakdown and completion ratio.
- Team: current members and permitted Add employee / Remove actions. Duplicate membership is rejected. Removing a member with unfinished tasks is blocked with actionable reassignment guidance.
- Tasks: table with title, assignee, status and logged hours. Filters for assignee and status. New task only for authorized users.
- Report: actual task counts, completion ratio and recorded hours by member. Explain the reporting scope. No invented velocity or budget metrics.

### Task create/edit
Fields: title, description, project and assignee. Within project details the project is fixed. Assignee choices include only active project members. If no members exist, explain Add an employee to this project before assigning a task. Retain typed values when validation fails.
Do not permit accidental project changes on an existing task. Reassignment must not transfer ownership of historical time entries.

### My tasks and task details
My tasks defaults to unfinished assigned work with status filters and project context. Task details show title, project link, assignee, description, textual workflow indicator and time-entry table.
To do exposes Start task. In progress exposes Mark completed. Completed shows a read-only banner. Proposed baseline: forward transitions only; no reopening or skipping. A completion confirmation explains that the task will become read-only and asks users to record any remaining time first.
Assignment/status changes must refresh current data. If the server rejects a stale edit because a task has already completed, preserve unsaved input where practical and explain that it cannot be saved.

### Log time
Form: work date, whole minutes and optional work note. Present durations as e.g. 1h 30m; persist integer minutes. Accept positive values only, with a documented maximum per entry. Proposed baseline: own assigned, In progress tasks only, no future work dates, and no normal-user changes after completion.
Explain that entries record work duration and are not a live timer or proof of clock-in attendance. Invalid membership/ownership must also fail on the API.

## 7. Shared component behaviour

- Tables: visible header, restrained row separators, 48px default row height, right-aligned numeric values, clear links and keyboard-accessible action menus. Do not add bulk actions unless implemented.
- Buttons: square; blue primary, neutral secondary, text/outline tertiary, red danger. Label actions specifically: Create project, Add employee, Log time. Disable duplicate submission while saving and announce completion or failure.
- Fields: persistent labels above inputs, visible required markers with legend, neutral field fill and discernible bottom border. Use native controls where practical. Associate errors and helper text programmatically.
- Status tags: To do uses a neutral background, In progress a pale blue background, Completed a pale green background; use dark text with verified contrast. A lock icon supplements Completed read-only text.
- Tabs: selected tab has blue underline and proper keyboard/ARIA behaviour; server-rendered navigation links are acceptable when presented as page sections rather than implementing a fake tab widget.
- Modal: use only for confirmations or short forms. Trap focus, support Escape, label the dialog and restore focus to its trigger. Prefer full-page forms for project/task editing.
- Progress: show completed / total beside percentage. Define percentage as completed tasks divided by total tasks. With zero tasks, display No tasks yet instead of a misleading 100%.

## 8. Required states and messages

Design loading, empty, no search results, validation failure, saving, saved, server failure, denied access and completed-task read-only states.

| Situation | Example copy |
| --- | --- |
| No projects, authorized manager | No projects yet. Create a project to organize your team's work. |
| Employee has no projects | You have not been assigned to a project yet. Contact your manager. |
| Empty search | No tasks match these filters. Clear filters. |
| Invalid project dates | End date must be on or after start date. |
| Invalid assignee | Choose an employee who belongs to this project. |
| Invalid duration | Enter a positive number of whole minutes. |
| Completed task | This task is completed and read-only. Contact an Admin if a correction is needed. |
| Failed save | Your changes could not be saved. Try again. |
| Denied or unavailable resource | This item is unavailable or you do not have permission to access it. |

Place validation beside the field and summarize multiple errors at the top. Preserve form input on failure. Use an accessible status region for short success messages; persistent business-rule explanations stay inline.

## 9. Accessibility and implementation checks

Target WCAG 2.2 AA; verify contrast rather than assuming every token pairing is compliant. Normal text needs 4.5:1 contrast; relevant large text and control boundaries need 3:1. Use meaningful headings, table captions and scoped column headers. Provide a skip link, visible keyboard focus, labelled icon buttons and sensible focus order.
Never use colour alone for statuses. Support 200% zoom and reduced motion. Avoid long tooltips as the only explanation. Confirm destructive operations with the affected item's name. Show localised readable dates such as 09 Oct 2026 while exchanging ISO dates with the API.
Use shared Django partials for shell, fields, buttons, status tags and table states. Centralize styling in tokens and component classes. Do not require a React migration or a Carbon React dependency to achieve the appearance.

## 10. Design review acceptance

- Every required feature has a reachable screen or action.
- Role differences are visible and enforced on the server.
- Dates, membership, assignment, transitions and completion locks have meaningful error states.
- Summary numbers and SQL-backed reports agree for seeded data.
- A manager can create a project, add an employee, create and assign a task.
- That employee can start it, log time and complete it; subsequent prohibited edits fail.
- Another employee and another manager cannot access unrelated records.
- All primary flows are keyboard usable and work at the specified viewport widths.
- Prototype-only features are clearly distinguished from implemented functionality.
- No visual element implies a feature that the submission does not provide.

## 11. Google Stitch handoff prompt

Design a desktop-first Project & Resource Management System for a small company, using this design.md as the governing specification. Use IBM/Carbon-inspired neutral surfaces, IBM Plex Sans, primary blue #0f62fe, charcoal #161616, square edges, thin borders and compact readable enterprise tables. The application has a charcoal 48px header, white 240px sidebar and light-gray work area with white panels. Use our product name and original branding.

Create a consistent linked screen set: Login; Manager Overview; Projects list; Create project; Project details with Overview, Team, Tasks and Report views; Create task; Employee My tasks; Task details with Log time and Completed read-only variants; and Admin Employees. Show role-aware actions, precise labels, real table columns, status tags and restrained summary tiles. Create desktop layouts only; mobile adaptations are excluded by the user.

Use a fictional Client Website Redesign project with employees Asha and Ravi. Show exactly To do, In progress and Completed task statuses. Include membership-only task assignment, date-range validation, time in minutes, task ownership and completed-task locking. Design empty, error and successful states. Use accessible contrast, visible focus and persistent field labels. Produce coherent application screens with a reusable component language; avoid promotional sections or controls for unspecified features. The result must be feasible with Django templates, HTML, CSS and JavaScript in the assignment timeline. Treat Admin completion overrides and detailed transition/time restrictions as the proposed policies documented above.

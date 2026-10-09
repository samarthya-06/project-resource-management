"""40 automated local browser/HTTP review cases, using an isolated test DB.

Run explicitly with QA40_EVIDENCE=1 to persist evidence. Ordinary pytest runs
exercise the assertions without overwriting the dated review artifacts.
"""

import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from django.db import connection
from django.utils import timezone
from playwright.sync_api import expect

from accounts.models import User
from projects import services
from projects.models import Project, ProjectMembership, Task, TimeEntry
from tests.conftest import TEST_PASSWORD
from tests.test_workspace_browser import demo as demo
from tests.test_workspace_browser import page as page

pytestmark = pytest.mark.django_db(transaction=True)
OUT = Path(__file__).resolve().parents[1] / "docs/evidence/qa40"
CASES = [
    ("R10", "Valid sign-in for all three roles", "Correct identity, Overview and role navigation."),
    (
        "R10",
        "Invalid and empty sign-in credentials",
        "Generic incorrect-credentials errors and required-field validation.",
    ),
    (
        "R01,R10",
        "New account password-change gate",
        "Workspace blocked until a strong matching password is set.",
    ),
    (
        "R10",
        "POST logout and protected-page access",
        "GET logout is 405; POST logout revokes workspace access.",
    ),
    (
        "R01",
        "Create account and reject duplicate identifier",
        "One record only; valid names retained and password cleared on failure.",
    ),
    (
        "R01,R10",
        "Edit account and explicitly reset password",
        "Blank reset preserves password; explicit reset requires password change.",
    ),
    (
        "R01,R03,R10",
        "Role changes with dependent relationships",
        "Invalid changes rejected without altering roles or relationships.",
    ),
    (
        "R01,R07,R10",
        "Deactivate account with open session and work history",
        "Existing session and new login denied; historical work retained.",
    ),
    (
        "R02,R06",
        "Create project with equal dates and correct owner",
        "Manager owns their project; Admin may choose another Manager.",
    ),
    (
        "R02,R06",
        "Invalid project dates and required fields",
        "Validation errors; useful input retained; no invalid record saved.",
    ),
    (
        "R02",
        "Project edit, persistence and no-results state",
        "Edit survives refresh and new login; unmatched search is empty.",
    ),
    (
        "R02,R10",
        "Project/team/report URL isolation",
        "Member reads allowed; foreign reads return 404 and Employee edits return 403.",
    ),
    (
        "R03",
        "Add active Employee and reject ineligible members",
        "Active Employee added; inactive account and Manager rejected.",
    ),
    (
        "R03",
        "Reject duplicate project membership",
        "Duplicate is rejected and only one membership remains.",
    ),
    (
        "R03,R04",
        "Block removal with unfinished assignments",
        "Actionable error; membership and assignments remain intact.",
    ),
    (
        "R03,R07,R10",
        "Remove member after reassignment",
        "Removal succeeds; original time attribution retained; access revoked.",
    ),
    (
        "R04",
        "Create and assign task through the desktop UI",
        "New task starts TODO and appears in project and assignee's My tasks.",
    ),
    (
        "R04",
        "No eligible members, blank title and nonmember selection",
        "Clear empty guidance and validation; no invalid task saved.",
    ),
    (
        "R04,R07",
        "Edit/reassign task with fixed project",
        "Task updated; project fixed; recorded work retains original contributor.",
    ),
    (
        "R05,R07",
        "Employee starts assigned task",
        "IN_PROGRESS enables Log time; starting creates no automatic time entry.",
    ),
    (
        "R05",
        "Reject skipping, reversing and reopening status",
        "Illegal transitions rejected and stored status unchanged.",
    ),
    (
        "R05",
        "Completion confirmation and cancellation",
        "Remaining-time guidance; cancel preserves status; confirm locks task.",
    ),
    (
        "R05,R07,R10",
        "Completed-task and time locks",
        "Manager/Employee direct URLs and API mutations reject prohibited changes.",
    ),
    (
        "R07",
        "Hours/minutes positive and boundary durations",
        "1h30m, 0h1m and 24h0m persist as 90, 1 and 1440 minutes.",
    ),
    (
        "R07",
        "Invalid hours/minutes retain useful input",
        "Zero, overflow, negative, fractional, minutes 60 and blanks rejected.",
    ),
    ("R07", "Reject future work dates", "HTML and API reject tomorrow without saving time."),
    (
        "R07",
        "Edit time and cancel/confirm deletion",
        "Prefill splits 90 into 1h30m; edit saves 120; confirmed delete reduces total.",
    ),
    (
        "R07,R10",
        "Time ownership and task-state permissions",
        "Other Employee, Manager and disallowed task states cannot mutate time.",
    ),
    (
        "R05,R07",
        "Stale time form after completion or reassignment",
        "403 with retained input; no late entry is saved.",
    ),
    (
        "R08",
        "Report totals, completion and empty project",
        "3 tasks, 2 complete, 180 minutes, 3 hours, 66.67%; empty project is zero.",
    ),
    (
        "R08,R10",
        "Role-scoped Overview and reports",
        "Admin sees all; Manager owned projects; Employee own work.",
    ),
    (
        "R05,R07,R10",
        "Explicit Admin completed-work corrections",
        "Correction retains COMPLETED, original task and original contributor.",
    ),
    (
        "R07,R08",
        "SQL/report agreement and persistence",
        "Read-only SQL agrees with ORM reports, including historical contributors.",
    ),
    (
        "R09",
        "REST workflow, partial updates and malformed input",
        "Valid workflow succeeds; omitted fields retained; invalid JSON/fields rejected.",
    ),
    (
        "R09,R10",
        "Forged ownership and privileged fields",
        "Protected fields rejected without altering ownership or privileges.",
    ),
    (
        "R09,R10",
        "List/filter/detail/report privacy and picker scope",
        "Foreign records/notes excluded; picker exposes only id and name.",
    ),
    (
        "R09,R10",
        "CSRF and strict JSON minutes",
        "Missing/wrong CSRF rejected; valid CSRF accepted; invalid numeric types rejected.",
    ),
    (
        "R10",
        "Stored XSS, search input and account permissions",
        "Markup escaped; search treated literally; non-Admins cannot manage accounts.",
    ),
    (
        "R02,R04,R05,R10",
        "Overview visibility before and after Employee starts a task",
        "Admin/Manager totals include the project; TODO task appears in Work in progress "
        "only after Start task; Employee sees own TODO work; foreign Manager excluded.",
    ),
    (
        "R02,R04,R07",
        "Protect history and allow safe deletion",
        "Dependent work protected; empty projects and tasks without history removable.",
    ),
]


class Review:
    def __init__(self, page, server, case):
        self.page, self.base, self.case = page, str(server), case
        self.events, self.images = [], []
        self.today = timezone.localdate().isoformat()

    def check(self, condition, message):
        self.events.append({"check": message, "passed": bool(condition)})
        assert condition, message

    def visit(self, path, status=200):
        response = self.page.goto(self.base + path)
        self.check(response.status == status, f"GET {path}: {response.status} (expected {status})")
        return response

    def login(self, name):
        self.page.context.clear_cookies()
        self.visit("/login/")
        self.fill("Login identifier", name + "@demo.local")
        self.fill("Password", TEST_PASSWORD, exact=True)
        self.click("Sign in")
        expect(self.page.get_by_role("heading", name="Overview", exact=True)).to_be_visible()
        self.events.append({"step": f"Browser sign-in as {name}; Overview displayed"})

    def fill(self, label, value, exact=False):
        self.page.get_by_label(label, exact=exact).fill(str(value))
        self.events.append(
            {
                "step": f"Fill {label}",
                "value": "[password omitted]" if "password" in label.lower() else str(value),
            }
        )

    def click(self, name):
        self.page.get_by_role("button", name=name, exact=True).click()
        self.events.append({"step": f"Click {name}"})

    def token(self):
        return next(c["value"] for c in self.page.context.cookies() if c["name"] == "csrftoken")

    def req(self, method, path, data=None, status=200, csrf=True):
        self.events.append(
            {
                "request": f"{method} {path}",
                "payload": {
                    key: "[chosen strong password]" if key == "password" else value
                    for key, value in (data or {}).items()
                },
            }
        )
        headers = {"X-CSRFToken": self.token()} if csrf else {}
        response = self.page.request.fetch(
            self.base + path, method=method, data=data, headers=headers
        )
        self.check(
            response.status == status, f"{method} {path}: {response.status} (expected {status})"
        )
        return (
            response.json()
            if response.status != 204 and "json" in response.headers.get("content-type", "")
            else response.text()
        )

    def html_post(self, path, data, status=200):
        response = self.page.request.post(
            self.base + path, form={**data, "csrfmiddlewaretoken": self.token()}
        )
        self.check(response.status == status, f"POST {path}: {response.status} (expected {status})")
        return response.text()

    def shot(self, name):
        if os.environ.get("QA40_EVIDENCE") == "1":
            OUT.mkdir(parents=True, exist_ok=True)
            filename = f"M{self.case:02}-{name}.png"
            self.page.evaluate("document.fonts.ready")
            self.page.screenshot(path=str(OUT / filename), full_page=True)
            self.images.append(filename)

    def invalid_submit(self, button):
        self.page.locator("form[data-saving]").evaluate("el => el.noValidate=true")
        self.click(button)
        expect(self.page.get_by_role("alert").first).to_be_visible()

    def account(self, username="qa40-new", **extra):
        return self.req(
            "POST",
            "/api/accounts/",
            {"username": username, "password": TEST_PASSWORD, "role": "EMPLOYEE", **extra},
            201,
        )["id"]

    def project_form(self, name="QA40 project"):
        self.visit("/projects/create/")
        self.fill("Project name", name)
        self.fill("Start date", self.today)
        self.fill("End date", self.today)

    def time_form(self, task, hours, minutes, note="QA40 work"):
        self.visit(f"/tasks/{task.pk}/")
        self.fill("Work date", self.today)
        self.fill("Hours", hours)
        self.fill("Minutes", minutes)
        self.fill("Work note", note)


@pytest.mark.parametrize("case", range(1, 41), ids=[f"M{i:02}" for i in range(1, 41)])
def test_review(case, page, live_server, demo, monkeypatch, settings):
    # Seed explicitly in development mode, then verify production error pages.
    settings.DEBUG = False
    # The test live server serves source assets; hashed build assets are separate.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    q = Review(page, live_server, case)
    page.set_viewport_size({"width": 1440, "height": 900})
    started = time.time()
    status, error = "PASS", ""
    try:
        q.check(connection.vendor == "postgresql", "Isolated PostgreSQL test database")
        q.check(not settings.DEBUG, "DEBUG=False: controlled production error responses")
        q.check(
            page.request.get(str(live_server) + "/static/css/workspace.css").status == 200,
            "Test live server serves source CSS (production asset build not exercised)",
        )
        execute_case(q, case, demo, monkeypatch)
        q.shot("final")
    except Exception as exc:
        status, error = "FAIL", f"{type(exc).__name__}: {exc}"
        q.shot("failure")
        raise
    finally:
        if os.environ.get("QA40_EVIDENCE") == "1":
            OUT.mkdir(parents=True, exist_ok=True)
            requirement, scenario, expected = CASES[case - 1]
            result = {
                "id": f"M{case:02}",
                "requirements": requirement,
                "scenario": scenario,
                "expected": expected,
                "status": status,
                "error": error,
                "method": (
                    "Automated pytest/Playwright Chromium browser/HTTP checks "
                    "with PostgreSQL readback"
                ),
                "started_utc": datetime.fromtimestamp(started, tz=UTC).isoformat(),
                "duration_seconds": round(time.time() - started, 2),
                "events": q.events,
                "screenshots": q.images,
            }
            (OUT / f"M{case:02}.json").write_text(json.dumps(result, indent=2))


def execute_case(q, case, project, monkeypatch):
    p = q.page
    asha = User.objects.get(username="asha@demo.local")
    ravi = User.objects.get(username="ravi@demo.local")
    neha = User.objects.get(username="neha@demo.local")
    dev = User.objects.get(username="dev@demo.local")
    task = Task.objects.get(project=project, title="Design homepage layout")
    todo = Task.objects.get(project=project, title="Review page content")
    done = Task.objects.get(project=project, title="Audit existing website")
    entry = TimeEntry.objects.filter(task=task).first()
    empty = Project.objects.get(demo_key="knowledge-base")
    today = timezone.localdate()
    if case == 1:
        for name, role in [("admin", "Admin"), ("neha", "Project Manager"), ("asha", "Employee")]:
            q.login(name)
            expect(p.locator("header")).to_contain_text(role)
            q.check(
                bool(p.get_by_role("link", name="Employees", exact=True).count())
                == (name == "admin"),
                f"{role}: correct Employees navigation",
            )
            q.shot(name)
    elif case == 2:
        for name in ["asha@demo.local", "does-not-exist@demo.local"]:
            q.visit("/login/")
            q.fill("Login identifier", name)
            q.fill("Password", "wrong", True)
            q.click("Sign in")
            expect(p.get_by_role("alert")).to_contain_text(
                "The login identifier or password is incorrect."
            )
            q.check(
                User.objects.filter(username=name).count() == (name.startswith("asha")),
                "Invalid sign-in creates no account",
            )
        q.shot("incorrect-credentials")
        q.visit("/login/")
        p.locator("form").evaluate("el=>el.noValidate=true")
        q.click("Sign in")
        q.check(p.locator(".field-errors").count() >= 2, "Blank credentials show required errors")
    elif case == 3:
        q.login("admin")
        uid = q.account()
        p.context.clear_cookies()
        q.visit("/login/")
        q.fill("Login identifier", "qa40-new")
        q.fill("Password", TEST_PASSWORD, True)
        q.click("Sign in")
        p.wait_for_url("**/password/change/")
        q.visit("/projects/")
        q.check(p.url.endswith("/password/change/"), "Direct project URL gated")
        for pw, repeat in [("123", "123"), ("Review-Changed!952", "Mismatch!123")]:
            q.fill("Old password", TEST_PASSWORD)
            q.fill("New password", pw, True)
            q.fill("New password confirmation", repeat)
            q.invalid_submit("Change password")
        q.shot("password-errors")
        q.fill("Old password", TEST_PASSWORD)
        q.fill("New password", "Review-Changed!952", True)
        q.fill("New password confirmation", "Review-Changed!952")
        q.click("Change password")
        expect(p.get_by_role("heading", name="Overview", exact=True)).to_be_visible()
        u = User.objects.get(pk=uid)
        q.check(
            not u.must_change_password and u.check_password("Review-Changed!952"),
            "Password changed and gate cleared in database",
        )
    elif case == 4:
        q.login("asha")
        q.req("GET", "/logout/", status=405)
        q.visit("/my-tasks/")
        q.click("Sign out")
        q.visit("/my-tasks/")
        q.check("/login/" in p.url, "Protected URL requires login after POST logout")
    elif case == 5:
        q.login("admin")
        for attempt in range(2):
            q.visit("/employees/create/")
            q.fill("First name", "Review")
            q.fill("Last name", "Employee")
            q.fill("Login identifier", "review-employee")
            q.fill("Initial password", TEST_PASSWORD)
            q.click("Create employee")
            if attempt:
                expect(p.get_by_role("alert")).to_contain_text("already exists")
                expect(p.get_by_label("First name")).to_have_value("Review")
                expect(p.get_by_label("Initial password")).to_have_value("")
        q.check(
            User.objects.filter(username="review-employee").count() == 1,
            "Duplicate rejected; one account stored",
        )
    elif case == 6:
        q.login("admin")
        old_hash = asha.password
        q.visit(f"/employees/{asha.pk}/edit/")
        q.fill("First name", "Asha Edited")
        q.click("Save employee")
        asha.refresh_from_db()
        q.check(
            asha.password == old_hash and not asha.must_change_password,
            "Blank reset preserves password and gate",
        )
        q.visit(f"/employees/{asha.pk}/edit/")
        q.fill("Reset password", "Reset-Review!835")
        q.click("Save employee")
        asha.refresh_from_db()
        q.check(
            asha.check_password("Reset-Review!835") and asha.must_change_password,
            "Explicit reset hashes new password and sets gate",
        )
        p.context.clear_cookies()
        q.visit("/login/")
        q.fill("Login identifier", asha.username)
        q.fill("Password", "Reset-Review!835", True)
        q.click("Sign in")
        p.wait_for_url("**/password/change/")
        q.check(
            p.url.endswith("/password/change/"),
            "Reset account signs in to mandatory password change",
        )
    elif case == 7:
        q.login("admin")
        for user, role in [(neha, "EMPLOYEE"), (asha, "ADMIN")]:
            q.visit(f"/employees/{user.pk}/edit/")
            p.get_by_label("Role", exact=False).first.select_option(role)
            p.get_by_label("I confirm this change of role.").check()
            q.click("Save employee")
            expect(p.get_by_role("alert")).to_be_visible()
            before = user.role
            user.refresh_from_db()
            q.check(user.role == before, "Role guard preserves existing role")
            q.shot(user.username.split("@")[0])
        q.check(
            Project.objects.get(pk=project.pk).manager_id == neha.pk
            and ProjectMembership.objects.filter(project=project, employee=asha).exists(),
            "Dependent relationships intact",
        )
    elif case == 8:
        q.login("asha")
        state = p.context.storage_state()
        q.login("admin")
        q.req("POST", f"/api/accounts/{asha.pk}/deactivate/", {}, 200)
        old_context = p.context.browser.new_context(storage_state=state)
        old_page = old_context.new_page()
        old_page.goto(q.base + "/my-tasks/")
        q.check("/login/" in old_page.url, "Existing inactive session denied")
        old_context.close()
        p.context.clear_cookies()
        q.visit("/login/")
        q.fill("Login identifier", asha.username)
        q.fill("Password", TEST_PASSWORD, True)
        q.click("Sign in")
        expect(p.get_by_role("alert")).to_contain_text("incorrect")
        q.check(
            Task.objects.filter(pk=task.pk).exists()
            and TimeEntry.objects.filter(pk=entry.pk, employee=asha).exists(),
            "Task and original contributor history preserved",
        )
    elif case == 9:
        q.login("neha")
        q.project_form()
        q.click("Create project")
        created = Project.objects.get(name="QA40 project")
        q.check(
            created.manager_id == neha.pk and created.start_date == created.end_date,
            "Equal dates accepted and Manager ownership assigned",
        )
        q.login("admin")
        q.project_form("Admin selected project")
        arjun = User.objects.get(username="arjun@demo.local")
        p.get_by_label("Project manager").select_option(str(arjun.pk))
        q.click("Create project")
        q.check(
            Project.objects.get(name="Admin selected project").manager_id == arjun.pk,
            "Admin-selected Manager stored",
        )
    elif case == 10:
        q.login("neha")
        for name, start, end in [
            ("Retained invalid project", q.today, str(today - timedelta(days=1))),
            ("", q.today, q.today),
            ("Missing dates", "", ""),
        ]:
            q.project_form(name)
            q.fill("Start date", start)
            q.fill("End date", end)
            q.invalid_submit("Create project")
            expect(p.get_by_label("Project name")).to_have_value(name)
            q.check(not Project.objects.filter(name=name).exists(), "Invalid project was not saved")
            q.shot("dates" if start and end else "required")
        from django.db import DatabaseError

        def simulated_failure(*args, **kwargs):
            raise DatabaseError("QA40 controlled failed-save simulation")

        with monkeypatch.context() as patch:
            patch.setattr(services, "create_project", simulated_failure)
            q.project_form("Retain after failed save")
            q.fill("Description", "Retain this useful description")
            q.click("Create project")
            expect(p.get_by_role("alert").first).to_contain_text("Try again")
            expect(p.get_by_label("Description")).to_have_value("Retain this useful description")
            q.shot("simulated-failed-save")
        q.check(
            not Project.objects.filter(name="Retain after failed save").exists(),
            "Simulated save failure retains input and stores no project",
        )
    elif case == 11:
        q.login("neha")
        q.visit(f"/projects/{project.pk}/edit/")
        q.fill("Project name", "QA40 persisted rename")
        q.click("Save project")
        p.reload()
        q.login("neha")
        q.visit(f"/projects/{project.pk}/")
        expect(p.get_by_role("heading", name="QA40 persisted rename")).to_be_visible()
        q.visit("/projects/?q=there-is-no-such-project")
        q.check(
            "No projects" in p.locator("main").inner_text(),
            "Project search renders no-results message",
        )
        q.visit(f"/projects/{empty.pk}/")
        q.check(
            "No tasks" in p.locator("main").inner_text() or "0%" in p.locator("main").inner_text(),
            "Empty project has zero-work summary",
        )
    elif case == 12:
        q.login("asha")
        for path in [
            f"/projects/{project.pk}/",
            f"/projects/{project.pk}/team/",
            f"/projects/{project.pk}/report/",
        ]:
            q.visit(path)
        for name in ["arjun", "dev"]:
            q.login(name)
            for suffix in ["", "team/", "report/", "edit/"]:
                q.visit(
                    f"/projects/{project.pk}/" + suffix,
                    403 if name == "dev" and suffix == "edit/" else 404,
                )
            q.shot(name + "-unavailable")
    elif case == 13:
        q.login("neha")
        q.visit(f"/projects/{empty.pk}/team/add/")
        p.get_by_label("Employee").select_option(str(dev.pk))
        q.click("Add employee")
        q.check(
            ProjectMembership.objects.filter(project=empty, employee=dev).exists(),
            "Active Employee membership saved",
        )
        for user in [User.objects.get(username="meera@demo.local"), neha]:
            q.req("POST", f"/api/projects/{empty.pk}/memberships/", {"employee_id": user.pk}, 400)
    elif case == 14:
        q.login("neha")
        q.req("POST", f"/api/projects/{project.pk}/memberships/", {"employee_id": asha.pk}, 400)
        q.check(
            ProjectMembership.objects.filter(project=project, employee=asha).count() == 1,
            "One membership after duplicate request",
        )
    elif case == 15:
        q.login("neha")
        q.visit(f"/projects/{project.pk}/team/{asha.pk}/remove/")
        p.get_by_label("I confirm this action.").check()
        q.click("Remove employee")
        expect(p.get_by_role("alert")).to_contain_text("unfinished")
        q.check(
            ProjectMembership.objects.filter(project=project, employee=asha).exists()
            and Task.objects.get(pk=task.pk).assignee_id == asha.pk,
            "Removal guard keeps membership and task",
        )
    elif case == 16:
        q.login("neha")
        for t in Task.objects.filter(project=project, assignee=asha).exclude(status="COMPLETED"):
            q.req("PATCH", f"/api/tasks/{t.pk}/", {"assignee_id": ravi.pk})
        q.req("DELETE", f"/api/projects/{project.pk}/memberships/{asha.pk}/", status=204)
        q.check(
            TimeEntry.objects.filter(pk=entry.pk, employee=asha).exists(),
            "Original contributor retained after reassignment/removal",
        )
        q.login("asha")
        q.visit(f"/tasks/{task.pk}/", 404)
        q.req("GET", f"/api/projects/{project.pk}/report/", status=404)
    elif case == 17:
        q.login("neha")
        q.visit(f"/projects/{project.pk}/tasks/create/")
        q.fill("Task title", "QA40 assigned task")
        p.get_by_label("Assignee").select_option(str(asha.pk))
        q.click("Create task")
        new = Task.objects.get(title="QA40 assigned task")
        q.check(
            new.status == "TODO" and new.project_id == project.pk and new.assignee_id == asha.pk,
            "TODO task and assignment stored",
        )
        q.visit(f"/projects/{project.pk}/tasks/?status=TODO&assignee={asha.pk}")
        expect(p.get_by_role("link", name=new.title, exact=True)).to_be_visible()
        q.login("asha")
        q.visit(f"/my-tasks/?status=TODO&project={project.pk}")
        expect(p.get_by_role("link", name=new.title, exact=True)).to_be_visible()
    elif case == 18:
        q.login("neha")
        q.visit(f"/projects/{empty.pk}/tasks/create/")
        expect(p.get_by_text("No eligible members.", exact=False)).to_be_visible()
        q.shot("no-eligible-members")
        q.visit(f"/projects/{project.pk}/tasks/create/")
        q.fill("Description", "Retain this description")
        q.invalid_submit("Create task")
        expect(p.get_by_label("Description")).to_have_value("Retain this description")
        q.req(
            "POST",
            "/api/tasks/",
            {"project_id": project.pk, "title": "Bad assignment", "assignee_id": dev.pk},
            400,
        )
        q.check(
            not Task.objects.filter(title="Bad assignment").exists(),
            "Nonmember assignment rejected",
        )
    elif case == 19:
        q.login("neha")
        q.visit(f"/tasks/{task.pk}/edit/")
        q.fill("Task title", "QA40 edited task")
        p.get_by_label("Assignee").select_option(str(ravi.pk))
        q.click("Save task")
        task.refresh_from_db()
        entry.refresh_from_db()
        q.check(
            task.assignee_id == ravi.pk
            and task.project_id == project.pk
            and entry.employee_id == asha.pk,
            "Reassignment retains fixed project and historical contributor",
        )
        q.req("PATCH", f"/api/tasks/{task.pk}/", {"project_id": empty.pk}, 400)
        q.visit(f"/tasks/{task.pk}/edit/")
        q.check(
            p.locator('select[name="project_id"],input[name="project_id"]').count() == 0,
            "Project is not editable",
        )
    elif case == 20:
        q.login("asha")
        q.visit(f"/tasks/{todo.pk}/")
        q.click("Start task")
        expect(p.get_by_role("heading", name="Log time", exact=True)).to_be_visible()
        todo.refresh_from_db()
        q.check(
            todo.status == "IN_PROGRESS" and TimeEntry.objects.filter(task=todo).count() == 0,
            "Start changes only status, not recorded duration",
        )
    elif case == 21:
        q.login("asha")
        q.req("PATCH", f"/api/tasks/{todo.pk}/", {"status": "COMPLETED"}, 400)
        q.req("PATCH", f"/api/tasks/{task.pk}/", {"status": "TODO"}, 400)
        q.req("PATCH", f"/api/tasks/{done.pk}/", {"status": "IN_PROGRESS"}, 403)
        q.check(
            list(
                Task.objects.filter(pk__in=[todo.pk, task.pk, done.pk])
                .order_by("pk")
                .values_list("status", flat=True)
            ).count("COMPLETED")
            == 1,
            "No illegal transition saved",
        )
    elif case == 22:
        q.login("asha")
        q.visit(f"/tasks/{task.pk}/complete/")
        expect(p.get_by_text("Record any remaining time first.", exact=False)).to_be_visible()
        q.shot("confirmation")
        p.get_by_role("link", name="Cancel", exact=True).click()
        q.check(Task.objects.get(pk=task.pk).status == "IN_PROGRESS", "Cancel retains status")
        q.visit(f"/tasks/{task.pk}/complete/")
        p.get_by_label("I confirm this action.").check()
        q.click("Mark completed")
        expect(p.get_by_text("Completed and read-only", exact=False)).to_be_visible()
        q.check(
            Task.objects.get(pk=task.pk).status == "COMPLETED"
            and p.get_by_role("button", name="Log time", exact=True).count() == 0,
            "Completion stored and Log time removed",
        )
    elif case == 23:
        finished_entry = TimeEntry.objects.filter(task=done).first()
        for name in ["asha", "neha"]:
            q.login(name)
            q.visit(f"/tasks/{done.pk}/")
            expect(p.get_by_text("Completed and read-only", exact=False)).to_be_visible()
            q.check(
                p.get_by_role("link", name="Edit task", exact=True).count() == 0,
                "Completed task edit hidden",
            )
            for path in [
                f"/tasks/{done.pk}/edit/",
                f"/time-entries/{finished_entry.pk}/edit/",
                f"/time-entries/{finished_entry.pk}/delete/",
            ]:
                q.visit(path, 403)
            for method, path, data in [
                ("PATCH", f"/api/tasks/{done.pk}/", {"status": "TODO"}),
                ("DELETE", f"/api/tasks/{done.pk}/", None),
                ("PATCH", f"/api/time-entries/{finished_entry.pk}/", {"minutes": 1}),
                ("DELETE", f"/api/time-entries/{finished_entry.pk}/", None),
            ]:
                q.req(method, path, data, 403)
            if name == "neha":
                q.req("PATCH", f"/api/tasks/{done.pk}/", {"assignee_id": ravi.pk}, 403)
        q.check(
            TimeEntry.objects.get(pk=finished_entry.pk).minutes == 240
            and Task.objects.get(pk=done.pk).status == "COMPLETED",
            "Rejected mutations leave completed work unchanged",
        )
    elif case == 24:
        q.login("asha")
        for hours, minutes, total in [(1, 30, 90), (0, 1, 1), (24, 0, 1440)]:
            q.time_form(task, hours, minutes, f"Boundary {total}")
            q.click("Log time")
            q.check(
                TimeEntry.objects.get(task=task, note=f"Boundary {total}").minutes == total,
                f"{hours}h {minutes}m persisted as {total} minutes",
            )
    elif case == 25:
        q.login("asha")
        count = TimeEntry.objects.count()
        for hours, minutes in [
            (0, 0),
            (24, 1),
            (-1, 0),
            (1.5, 0),
            (0, 60),
            (0, 1.5),
            ("", 10),
            (1, ""),
        ]:
            q.time_form(task, hours, minutes, "Retain useful note")
            p.locator('form[action$="/time/add/"]').evaluate("el=>el.noValidate=true")
            q.click("Log time")
            expect(p.get_by_role("alert")).to_be_visible()
            expect(p.get_by_label("Work note")).to_have_value("Retain useful note")
            expect(p.get_by_label("Work date")).to_have_value(q.today)
            q.check(
                TimeEntry.objects.count() == count,
                f"Invalid duration {hours!r}h {minutes!r}m rejected; note/date retained",
            )
        q.shot("validation")
    elif case == 26:
        q.login("asha")
        count = TimeEntry.objects.count()
        tomorrow = str(today + timedelta(days=1))
        q.time_form(task, 1, 0)
        q.fill("Work date", tomorrow)
        p.locator('form[action$="/time/add/"]').evaluate("el=>el.noValidate=true")
        q.click("Log time")
        expect(p.get_by_role("alert")).to_contain_text("future")
        q.req(
            "POST",
            "/api/time-entries/",
            {"task_id": task.pk, "work_date": tomorrow, "minutes": 60},
            400,
        )
        q.check(TimeEntry.objects.count() == count, "Future date creates no time record")
    elif case == 27:
        services.update_time_entry(asha, entry.pk, minutes=90)
        q.login("asha")
        q.visit(f"/time-entries/{entry.pk}/edit/")
        expect(p.get_by_label("Hours")).to_have_value("1")
        expect(p.get_by_label("Minutes")).to_have_value("30")
        q.fill("Hours", 2)
        q.fill("Minutes", 0)
        q.click("Save time")
        q.check(
            TimeEntry.objects.get(pk=entry.pk).minutes == 120,
            "Edited duration stored as 120 minutes",
        )
        original_total = sum(TimeEntry.objects.filter(task=task).values_list("minutes", flat=True))
        q.time_form(task, 0, 30, "Delete this test entry")
        q.click("Log time")
        extra = TimeEntry.objects.get(task=task, note="Delete this test entry")
        q.visit(f"/time-entries/{extra.pk}/delete/")
        p.get_by_role("link", name="Cancel", exact=True).click()
        q.check(TimeEntry.objects.filter(pk=extra.pk).exists(), "Cancel preserves time entry")
        q.visit(f"/time-entries/{extra.pk}/delete/")
        p.get_by_label("I confirm this action.").check()
        q.shot("delete-confirmation")
        q.click("Delete time entry")
        q.check(
            not TimeEntry.objects.filter(pk=extra.pk).exists(),
            "Confirmed deletion removes only selected entry",
        )
        q.check(
            sum(TimeEntry.objects.filter(task=task).values_list("minutes", flat=True))
            == original_total,
            "Confirmed deletion restores the original task time total",
        )
    elif case == 28:
        original_minutes = entry.minutes
        for name, code in [("ravi", 404), ("neha", 403)]:
            q.login(name)
            q.req("PATCH", f"/api/time-entries/{entry.pk}/", {"minutes": 1}, code)
            q.req("DELETE", f"/api/time-entries/{entry.pk}/", status=code)
        q.login("asha")
        for t in [todo, done]:
            q.req(
                "POST",
                "/api/time-entries/",
                {"task_id": t.pk, "work_date": q.today, "minutes": 60},
                403,
            )
        services.update_task(neha, task.pk, assignee_id=ravi.pk)
        q.req("PATCH", f"/api/time-entries/{entry.pk}/", {"minutes": 1}, 403)
        q.check(
            TimeEntry.objects.get(pk=entry.pk).minutes == original_minutes,
            "Time ownership/state failures leave entry intact",
        )
    elif case == 29:
        q.login("asha")
        for t, new_status in [(task, "COMPLETED"), (todo, "reassign")]:
            if t.status == "TODO":
                services.update_task(asha, t.pk, status="IN_PROGRESS")
            q.time_form(t, 1, 0, "Retained stale note")
            second = p.context.browser.new_context()
            second_page = second.new_page()
            other = Review(second_page, q.base, case)
            other.login("neha")
            other.req(
                "PATCH",
                f"/api/tasks/{t.pk}/",
                {"status": new_status} if new_status != "reassign" else {"assignee_id": ravi.pk},
            )
            second.close()
            q.events.extend(other.events)
            with p.expect_response(lambda response: response.url.endswith("/time/add/")) as saved:
                q.click("Log time")
            q.check(saved.value.status == 403, "Stale time POST returns 403")
            expect(p.get_by_role("alert")).to_be_visible()
            expect(p.get_by_label("Work note")).to_have_value("Retained stale note")
            q.check(
                not TimeEntry.objects.filter(task=t, note="Retained stale note").exists(),
                "Stale form saves no entry and retains note",
            )
            q.shot(new_status.lower())
    elif case == 30:
        q.login("neha")
        pid = q.req(
            "POST",
            "/api/projects/",
            {"name": "QA40 report", "start_date": q.today, "end_date": q.today},
            201,
        )["id"]
        q.req("POST", f"/api/projects/{pid}/memberships/", {"employee_id": asha.pk}, 201)
        ids = [
            q.req(
                "POST",
                "/api/tasks/",
                {"project_id": pid, "title": f"Report task {n}", "assignee_id": asha.pk},
                201,
            )["id"]
            for n in range(3)
        ]
        q.login("asha")
        for tid, minutes in zip(ids[:2], [90, 30]):
            q.req("PATCH", f"/api/tasks/{tid}/", {"status": "IN_PROGRESS"})
            q.req(
                "POST",
                "/api/time-entries/",
                {"task_id": tid, "work_date": q.today, "minutes": minutes},
                201,
            )
        q.req(
            "POST",
            "/api/time-entries/",
            {"task_id": ids[0], "work_date": q.today, "minutes": 60},
            201,
        )
        for tid in ids[:2]:
            q.req("PATCH", f"/api/tasks/{tid}/", {"status": "COMPLETED"})
        q.login("neha")
        report = q.req("GET", f"/api/projects/{pid}/report/")
        q.check(
            (
                report["total_tasks"],
                report["completed_tasks"],
                report["total_minutes"],
                report["total_hours"],
                report["completion_percentage"],
            )
            == (3, 2, 180, 3, 66.67),
            "Report is 3 tasks, 2 completed, 180 min, 3h, 66.67%",
        )
        q.events.append({"report": report})
        q.visit(f"/projects/{pid}/report/")
        expect(p.locator("tfoot")).to_contain_text("180")
        q.shot("report")
        zero = q.req("GET", f"/api/projects/{empty.pk}/report/")
        q.check(
            zero["total_tasks"] == zero["total_minutes"] == zero["completion_percentage"] == 0,
            "Zero-task report returns zeros",
        )
    elif case == 31:
        for name, expected in [("admin", 4), ("neha", 3), ("asha", 2)]:
            q.login(name)
            overview = q.req("GET", "/api/overview/")
            q.check(
                overview["project_count"] == expected, f"{name} sees {expected} authorized projects"
            )
            report = q.req("GET", f"/api/projects/{project.pk}/report/")
            q.check(
                report["total_minutes"] == (420 if name == "asha" else 720),
                f"{name} project report has correctly scoped minutes",
            )
            if name == "asha":
                q.check(
                    all(row["employee_id"] == asha.pk for row in report["contributors"]),
                    "Employee contributor report includes own work only",
                )
    elif case == 32:
        q.login("admin")
        finished_entry = TimeEntry.objects.filter(task=done).first()
        q.visit(f"/tasks/{done.pk}/correction/")
        q.fill("Task title", "QA40 corrected audit")
        p.get_by_label("Assignee").select_option(str(ravi.pk))
        q.click("Correct completed task")
        q.visit(f"/time-entries/{finished_entry.pk}/correction/")
        expect(p.get_by_text("Original contributor: Asha Deshmukh.", exact=False)).to_be_visible()
        q.fill("Hours", 4)
        q.fill("Minutes", 10)
        q.click("Correct time entry")
        done.refresh_from_db()
        finished_entry.refresh_from_db()
        q.check(
            done.status == "COMPLETED"
            and done.assignee_id == ravi.pk
            and finished_entry.employee_id == asha.pk
            and finished_entry.task_id == done.pk
            and finished_entry.minutes == 250,
            "Admin correction preserves completed status and original identity",
        )
        q.req("PATCH", f"/api/tasks/{done.pk}/correction/", {"status": "TODO"}, 400)
    elif case == 33:
        from scripts.verify_project_reports import verify

        q.login("neha")
        q.req("PATCH", f"/api/tasks/{task.pk}/", {"assignee_id": ravi.pk})
        result = verify()
        q.events.append({"sql_comparison": result})
        sql_path = Path(__file__).resolve().parents[1] / "sql/project_reports.sql"
        with connection.cursor() as cursor:
            for label, query in zip(
                ["sql_project_rows", "sql_contributor_rows"],
                [query.strip() for query in sql_path.read_text().split(";") if query.strip()],
            ):
                cursor.execute(query)
                columns = [column[0] for column in cursor.description]
                q.events.append(
                    {
                        label: [
                            {
                                key: float(value) if hasattr(value, "as_tuple") else value
                                for key, value in zip(columns, row)
                            }
                            for row in cursor.fetchall()
                        ]
                    }
                )
        q.check(
            result["result"] == "MATCH" and result["projects_compared"] == 4,
            "Both SQL queries agree with all four project reports and historical contributors",
        )
        q.visit(f"/projects/{project.pk}/report/")
        p.reload()
        q.login("neha")
        q.visit(f"/projects/{project.pk}/report/")
        expect(p.locator("tfoot")).to_contain_text("720")
    elif case == 34:
        q.visit("/login/")
        q.req("GET", "/api/projects/", status=403, csrf=False)
        q.login("neha")
        result = q.req(
            "POST",
            "/api/projects/",
            {"name": "HTTP review", "start_date": q.today, "end_date": q.today},
            201,
        )
        pid = result["id"]
        q.req("PATCH", f"/api/projects/{pid}/", {"description": "Partial PATCH"})
        q.req("PUT", f"/api/projects/{pid}/", {"name": "Partial PUT"})
        q.check(
            Project.objects.get(pk=pid).description == "Partial PATCH"
            and Project.objects.get(pk=pid).start_date == today,
            "Partial PUT/PATCH retain omitted fields",
        )
        q.req("POST", f"/api/projects/{pid}/memberships/", {"employee_id": asha.pk}, 201)
        tid = q.req(
            "POST",
            "/api/tasks/",
            {"project_id": pid, "title": "HTTP work", "assignee_id": asha.pk},
            201,
        )["id"]
        q.login("asha")
        q.req("PATCH", f"/api/tasks/{tid}/", {"status": "IN_PROGRESS"})
        q.req(
            "POST", "/api/time-entries/", {"task_id": tid, "work_date": q.today, "minutes": 45}, 201
        )
        q.req("PATCH", f"/api/tasks/{tid}/", {"status": "COMPLETED"})
        q.login("neha")
        q.req("POST", "/api/tasks/", {"project_id": pid}, 400)
        q.req("POST", "/api/projects/", {"name": "Missing dates"}, 400)
        response = p.request.patch(
            q.base + f"/api/projects/{pid}/",
            data="{bad",
            headers={"Content-Type": "application/json", "X-CSRFToken": q.token()},
        )
        q.check(response.status == 400, "Malformed JSON returns 400")
    elif case == 35:
        q.login("neha")
        for path, data in [
            (f"/api/projects/{project.pk}/", {"manager_id": dev.pk}),
            (f"/api/tasks/{task.pk}/", {"project_id": empty.pk}),
            (f"/api/tasks/{task.pk}/", {"id": 999}),
        ]:
            q.req("PATCH", path, data, 400)
        q.login("asha")
        for data in [{"employee_id": ravi.pk}, {"task_id": todo.pk}]:
            q.req("PATCH", f"/api/time-entries/{entry.pk}/", data, 400)
        q.login("admin")
        for field in [
            "is_staff",
            "is_superuser",
            "must_change_password",
            "groups",
            "user_permissions",
        ]:
            q.req("PATCH", f"/api/accounts/{asha.pk}/", {field: True}, 400)
        q.check(
            Project.objects.get(pk=project.pk).manager_id == neha.pk
            and TimeEntry.objects.get(pk=entry.pk).employee_id == asha.pk
            and not User.objects.get(pk=asha.pk).is_superuser,
            "Ownership/contributor/privileges unchanged",
        )
    elif case == 36:
        for name in ["arjun", "dev"]:
            q.login(name)
            for path in [
                f"/api/projects/{project.pk}/",
                f"/api/tasks/{task.pk}/",
                f"/api/projects/{project.pk}/report/",
                f"/api/time-entries/{entry.pk}/",
            ]:
                q.req("GET", path, status=404)
            for path in [
                f"/api/tasks/?project={project.pk}",
                f"/api/time-entries/?project={project.pk}",
            ]:
                q.check(q.req("GET", path)["count"] == 0, "Foreign filter contains zero records")
            q.check(
                project.pk not in [row["id"] for row in q.req("GET", "/api/projects/")["results"]],
                "Foreign project absent from list",
            )
        q.login("ravi")
        q.req("GET", f"/api/time-entries/{entry.pk}/", status=404)
        q.visit(f"/tasks/{task.pk}/")
        q.check(
            entry.note not in p.locator("main").inner_text(),
            "Other Employee's detailed time note absent from HTML",
        )
        for path in ["/api/tasks/", f"/api/projects/{project.pk}/report/"]:
            text = json.dumps(q.req("GET", path))
            q.check(
                entry.note not in text and "password" not in text and "is_staff" not in text,
                "No private notes/password/privilege fields in serialization",
            )
        q.login("neha")
        options = q.req("GET", f"/api/projects/{project.pk}/employee-options/")["results"]
        q.check(
            all(set(row) == {"id", "name"} for row in options), "Picker fields limited to id/name"
        )
        q.check(
            all(
                User.objects.get(pk=row["id"]).is_active
                and User.objects.get(pk=row["id"]).role == "EMPLOYEE"
                for row in options
            ),
            "Picker includes active Employees only",
        )
    elif case == 37:
        q.visit("/login/")
        response = p.request.post(
            q.base + "/login/", form={"username": asha.username, "password": TEST_PASSWORD}
        )
        q.check(response.status == 403, "Login without CSRF returns 403")
        q.login("asha")
        q.req("PATCH", f"/api/tasks/{task.pk}/", {"status": "IN_PROGRESS"}, 403, csrf=False)
        response = p.request.patch(
            q.base + f"/api/tasks/{task.pk}/",
            data={"status": "IN_PROGRESS"},
            headers={"X-CSRFToken": "x" * 32},
        )
        q.check(response.status == 403, "Wrong CSRF token returns 403")
        q.req("PATCH", f"/api/tasks/{task.pk}/", {"status": "IN_PROGRESS"})
        for value in [True, False, 1.5, 1.0, "60", None, 0, 1441]:
            q.req(
                "POST",
                "/api/time-entries/",
                {"task_id": task.pk, "work_date": q.today, "minutes": value},
                400,
            )
        q.req(
            "POST",
            "/api/time-entries/",
            {"task_id": task.pk, "work_date": q.today, "minutes": 60},
            201,
        )
    elif case == 38:
        q.login("neha")
        payload = '<script>window.qa40xss=1</script><img src=x onerror="window.qa40xss=2">'
        q.req("PATCH", f"/api/tasks/{task.pk}/", {"description": payload})
        q.visit(f"/tasks/{task.pk}/")
        q.check(
            p.evaluate("window.qa40xss===undefined"), "Stored markup does not execute JavaScript"
        )
        q.check(
            payload in p.locator("main").inner_text(), "Markup displayed as literal escaped text"
        )
        q.visit("/projects/?q=%27%20OR%201%3D1--")
        q.check(
            "No projects" in p.locator("main").inner_text(),
            "SQL-like search is literal and does not broaden results",
        )
        for name in ["neha", "asha"]:
            q.login(name)
            q.visit("/employees/", 403)
            q.req("GET", "/api/accounts/", status=403)
            q.req(
                "POST", "/api/accounts/", {"username": "forbidden", "password": TEST_PASSWORD}, 403
            )
    elif case == 39:
        q.login("neha")
        new = q.req(
            "POST",
            "/api/projects/",
            {
                "name": "Overview workflow project",
                "start_date": q.today,
                "end_date": q.today,
            },
            201,
        )
        q.req("POST", f"/api/projects/{new['id']}/memberships/", {"employee_id": asha.pk}, 201)
        created = q.req(
            "POST",
            "/api/tasks/",
            {
                "project_id": new["id"],
                "title": "Overview workflow task",
                "assignee_id": asha.pk,
            },
            201,
        )
        for name, project_count in [("neha", 4), ("admin", 5)]:
            q.login(name)
            q.visit("/")
            q.check(
                "Overview workflow task" not in p.locator("table").inner_text(),
                f"{name}: TODO task excluded from Work in progress",
            )
            q.check(
                q.req("GET", "/api/overview/")["project_count"] == project_count,
                f"{name}: new project included in summary",
            )
            q.shot(name + "-before-start")
        q.login("asha")
        q.visit("/")
        expect(p.get_by_role("link", name="Overview workflow task", exact=True)).to_be_visible()
        q.check(True, "Employee Overview includes own TODO task")
        q.visit(f"/tasks/{created['id']}/")
        q.click("Start task")
        q.check(
            Task.objects.get(pk=created["id"]).status == "IN_PROGRESS",
            "Employee Start task button persists IN_PROGRESS",
        )
        for name in ["neha", "admin"]:
            q.login(name)
            q.visit("/")
            expect(
                p.locator("table").get_by_role("link", name="Overview workflow task", exact=True)
            ).to_be_visible()
            expect(
                p.locator("table").get_by_role("link", name="Overview workflow project", exact=True)
            ).to_be_visible()
            q.check(True, f"{name}: started task and project visible in Work in progress")
            q.shot(name + "-after-start")
        q.login("arjun")
        q.visit("/")
        q.check(
            "Overview workflow task" not in p.locator("main").inner_text(),
            "Foreign Manager cannot see the task",
        )
    elif case == 40:
        q.login("neha")
        q.req("DELETE", f"/api/projects/{project.pk}/", status=400)
        q.req("DELETE", f"/api/tasks/{task.pk}/", status=400)
        q.req("DELETE", f"/api/tasks/{done.pk}/", status=403)
        q.check(
            Project.objects.filter(pk=project.pk).exists()
            and TimeEntry.objects.filter(pk=entry.pk).exists(),
            "Dependent project/task/time history preserved",
        )
        q.req("DELETE", f"/api/projects/{empty.pk}/", status=204)
        q.req("DELETE", f"/api/tasks/{todo.pk}/", status=204)
        q.check(
            not Project.objects.filter(pk=empty.pk).exists()
            and not Task.objects.filter(pk=todo.pk).exists(),
            "Safe empty project and task deleted",
        )

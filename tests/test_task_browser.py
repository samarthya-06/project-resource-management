"""Automated desktop journeys on PostgreSQL test data, not human manual cases."""

from pathlib import Path

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from accounts.models import User
from projects.models import Project, Task, TimeEntry
from tests.test_workspace_browser import demo as demo
from tests.test_workspace_browser import login, shell_checks
from tests.test_workspace_browser import page as page

pytestmark = pytest.mark.django_db(transaction=True)
EVIDENCE = Path(__file__).resolve().parents[1] / "docs/evidence/tasks"


def capture(page, name):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(EVIDENCE / f"{name}.png"), full_page=True)


def signout(page):
    page.get_by_role("button", name="Sign out", exact=True).click()


def test_manager_employee_complete_desktop_workflow(page, live_server):
    login(page, live_server, "neha@demo.local")
    page.get_by_role("link", name="Create project", exact=True).click()
    page.get_by_label("Project name").fill("Task browser project")
    today = timezone.localdate().isoformat()
    page.get_by_label("Start date").fill(today)
    page.get_by_label("End date").fill(today)
    page.get_by_role("button", name="Create project", exact=True).click()
    page.get_by_role("link", name="Task browser project", exact=True).click()
    page.get_by_role("link", name="Team", exact=True).click()
    page.get_by_role("link", name="Add employee", exact=True).click()
    page.get_by_label("Employee", exact=False).select_option(label="Dev Rao")
    page.get_by_role("button", name="Add employee", exact=True).click()
    page.get_by_role("link", name="Tasks", exact=True).click()
    expect(page.get_by_text("No tasks yet.", exact=True)).to_be_visible()
    capture(page, "project-empty-tasks")
    page.get_by_role("link", name="Create task", exact=True).click()
    page.get_by_label("Task title").focus()
    page.keyboard.type("Review desktop workflow")
    page.keyboard.press("Tab")
    expect(page.get_by_label("Description")).to_be_focused()
    assert (
        page.get_by_label("Description").evaluate("el => getComputedStyle(el).outlineStyle")
        == "solid"
    )
    page.keyboard.type("Check navigation, work recording and completion feedback.")
    page.get_by_label("Assignee").select_option(label="Dev Rao")
    capture(page, "manager-create-task")
    page.get_by_role("button", name="Create task", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Task created")
    page.get_by_role("link", name="Review desktop workflow", exact=True).click()
    task = Task.objects.get(title="Review desktop workflow")
    project = task.project
    capture(page, "manager-task-detail")
    page.get_by_role("link", name="Edit task", exact=True).click()
    page.get_by_label("Task title").fill("Review complete desktop workflow")
    capture(page, "manager-edit-task")
    page.get_by_role("button", name="Save task", exact=True).click()
    signout(page)
    login(page, live_server, "dev@demo.local")
    page.get_by_role("link", name="My tasks", exact=True).click()
    shell_checks(page)
    capture(page, "employee-my-tasks")
    page.get_by_role("link", name="Review complete desktop workflow", exact=True).click()
    capture(page, "employee-todo")
    page.get_by_role("button", name="Start task", exact=True).click()
    expect(page.get_by_role("heading", name="Log time", exact=True)).to_be_visible()
    page.get_by_label("Work date").fill(today)
    page.get_by_label("Minutes").fill("90")
    page.get_by_label("Work note").fill("Keyboard and navigation review")
    page.get_by_role("button", name="Log time", exact=True).click()
    entry = TimeEntry.objects.get(task=task)
    expect(page.get_by_text("1h 30m", exact=True).first).to_be_visible()
    shell_checks(page)
    capture(page, "employee-in-progress")
    page.get_by_role("link", name=f"Edit time entry {entry.pk}", exact=True).click()
    page.get_by_label("Minutes").fill("120")
    capture(page, "employee-edit-time")
    page.get_by_role("button", name="Save time", exact=True).click()
    # Bypass native numeric validation to verify the server error and retained note.
    page.get_by_label("Minutes").fill("1.5")
    page.get_by_label("Work note").fill("Retain this note after invalid minutes")
    page.locator('form[action$="/time/add/"]').evaluate("el => el.noValidate = true")
    page.get_by_role("button", name="Log time", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Enter a whole number")
    expect(page.get_by_label("Work note")).to_have_value("Retain this note after invalid minutes")
    expect(page.locator(".error-summary")).to_be_focused()
    capture(page, "employee-time-validation")
    page.get_by_label("Minutes").fill("30")
    page.get_by_role("button", name="Log time", exact=True).click()
    extra = TimeEntry.objects.filter(task=task).exclude(pk=entry.pk).get()
    page.get_by_role("link", name=f"Delete time entry {extra.pk}", exact=True).click()
    capture(page, "employee-delete-time-confirmation")
    page.get_by_label("I confirm this action.").check()
    page.get_by_role("button", name="Delete time entry", exact=True).click()
    assert not TimeEntry.objects.filter(pk=extra.pk).exists()
    zoom = page.context.browser.new_context(
        viewport={"width": 720, "height": 450},
        device_scale_factor=2,
        storage_state=page.context.storage_state(),
    )
    zoom_page = zoom.new_page()
    zoom_page.goto(str(live_server) + f"/tasks/{task.pk}/")
    assert zoom_page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    expect(zoom_page.get_by_label("Minutes")).to_be_visible()
    expect(zoom_page.get_by_role("link", name="Mark completed", exact=True)).to_be_visible()
    capture(zoom_page, "employee-time-200-percent")
    zoom.close()
    page.get_by_role("link", name="Mark completed", exact=True).click()
    expect(page.get_by_text("Record any remaining time first.", exact=False)).to_be_visible()
    capture(page, "employee-completion-confirmation")
    page.get_by_label("I confirm this action.").check()
    page.get_by_role("button", name="Mark completed", exact=True).click()
    expect(page.get_by_text("Completed and read-only", exact=False)).to_be_visible()
    assert page.get_by_role("link", name="Edit time", exact=False).count() == 0
    assert page.get_by_role("button", name="Log time", exact=True).count() == 0
    capture(page, "employee-completed")
    token = page.locator('input[name="csrfmiddlewaretoken"]').first.input_value()
    response = page.request.post(
        str(live_server) + f"/time-entries/{entry.pk}/edit/",
        form={
            "work_date": today,
            "minutes": "999",
            "note": "Forbidden",
            "csrfmiddlewaretoken": token,
        },
    )
    assert response.status == 403
    signout(page)
    login(page, live_server, "neha@demo.local")
    page.goto(str(live_server) + f"/tasks/{task.pk}/")
    assert page.get_by_role("link", name="Edit task", exact=True).count() == 0
    capture(page, "manager-completed-task")
    token = page.locator('input[name="csrfmiddlewaretoken"]').first.input_value()
    response = page.request.post(
        str(live_server) + f"/tasks/{task.pk}/edit/",
        form={
            "title": "Forbidden",
            "description": "",
            "assignee_id": "",
            "csrfmiddlewaretoken": token,
        },
    )
    assert response.status == 403
    page.goto(str(live_server) + f"/projects/{project.pk}/report/")
    expect(page.locator("tfoot")).to_contain_text("120")
    expect(page.locator("tfoot")).to_contain_text("2h")
    capture(page, "manager-workflow-report")
    task.refresh_from_db()
    entry.refresh_from_db()
    assert task.status == "COMPLETED" and entry.minutes == 120


def test_admin_corrections_and_foreign_access(page, live_server, demo):
    asha = User.objects.get(username="asha@demo.local")
    task = Task.objects.get(project=demo, title="Audit existing website")
    entry = TimeEntry.objects.get(task=task)
    original = entry.employee_id
    login(page, live_server, "admin@demo.local")
    page.goto(str(live_server) + f"/tasks/{task.pk}/")
    capture(page, "admin-completed-task")
    page.get_by_role("link", name="Correct completed task", exact=True).click()
    page.get_by_label("Task title").fill("Corrected website audit")
    page.get_by_label("Assignee").select_option(label="Ravi Kulkarni")
    capture(page, "admin-task-correction")
    page.get_by_role("button", name="Correct completed task", exact=True).click()
    page.get_by_role("link", name=f"Correct time entry {entry.pk}", exact=True).click()
    expect(page.get_by_text("Original contributor: Asha Deshmukh.", exact=False)).to_be_visible()
    page.get_by_label("Minutes").fill("250")
    capture(page, "admin-time-correction")
    page.get_by_role("button", name="Correct time entry", exact=True).click()
    task.refresh_from_db()
    entry.refresh_from_db()
    assert (
        task.status == "COMPLETED"
        and entry.employee_id == original
        and entry.task_id == task.pk
        and entry.minutes == 250
    )
    assert task.assignee.username == "ravi@demo.local"
    signout(page)
    for username in ["arjun@demo.local", "dev@demo.local"]:
        login(page, live_server, username)
        assert page.goto(str(live_server) + f"/tasks/{task.pk}/").status == 404
        assert page.goto(str(live_server) + f"/projects/{demo.pk}/tasks/").status == 404
        page.goto(str(live_server) + "/")
        signout(page)
    login(page, live_server, "ravi@demo.local")
    page.goto(str(live_server) + f"/tasks/{task.pk}/")
    assert "Audited navigation" not in page.content()
    assert "Correct time" not in page.content()
    assert page.get_by_role("link", name="Correct completed task", exact=True).count() == 0
    # Original contributor can still read their own historical entry after reassignment.
    signout(page)
    login(page, live_server, "asha@demo.local")
    page.goto(str(live_server) + f"/tasks/{task.pk}/")
    expect(page.get_by_text("4h 10m", exact=True).first).to_be_visible()
    assert entry.employee_id == asha.pk
    empty = Project.objects.get(demo_key="knowledge-base")
    signout(page)
    login(page, live_server, "neha@demo.local")
    page.goto(str(live_server) + f"/projects/{empty.pk}/tasks/create/")
    expect(page.get_by_text("No eligible members.", exact=False)).to_be_visible()
    capture(page, "manager-no-eligible-member")


def test_seed_task_artboards_and_filters(page, live_server, demo):
    login(page, live_server, "neha@demo.local")
    page.goto(str(live_server) + f"/projects/{demo.pk}/tasks/")
    shell_checks(page)
    capture(page, "manager-project-tasks")
    page.get_by_label("Status", exact=False).select_option("TODO")
    page.get_by_label("Assignee", exact=False).select_option(label="Asha Deshmukh")
    page.get_by_role("button", name="Apply filters", exact=True).click()
    expect(page.get_by_role("link", name="Review page content", exact=True)).to_be_visible()
    assert page.get_by_role("link", name="Implement navigation", exact=True).count() == 0
    signout(page)
    login(page, live_server, "asha@demo.local")
    page.get_by_role("link", name="My tasks", exact=True).click()
    capture(page, "employee-seed-my-tasks")
    page.get_by_label("Status", exact=False).select_option("COMPLETED")
    page.get_by_label("Project", exact=False).select_option(str(demo.pk))
    page.get_by_role("button", name="Apply filters", exact=True).click()
    expect(page.get_by_role("link", name="Audit existing website", exact=True)).to_be_visible()
    page.get_by_role("link", name="Clear filters", exact=True).click()
    page.get_by_role("link", name="Design homepage layout", exact=True).click()
    capture(page, "employee-seed-in-progress")

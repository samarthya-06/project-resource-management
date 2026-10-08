"""Automated desktop checks on isolated test data, not human manual evidence."""

from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.core.management import call_command
from django.db import connections
from playwright.sync_api import expect, sync_playwright

from accounts.models import User
from projects.models import Project, ProjectMembership
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db(transaction=True)
EVIDENCE = Path(__file__).resolve().parents[1] / "docs/evidence/workspace"


@pytest.fixture
def demo(settings):
    settings.DEBUG = True
    settings.DEMO_PASSWORD = TEST_PASSWORD
    call_command("seed_demo", stdout=StringIO())
    return Project.objects.get(demo_key="website-redesign")


@pytest.fixture
def page(demo, live_server, monkeypatch):
    # Playwright's synchronous driver uses an event loop in this test thread.
    # Only this isolated, serial test thread needs synchronous ORM assertions;
    # the application server and production settings keep Django's async guard.
    monkeypatch.setenv("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context()
        yield context.new_page()
        context.close()
        browser.close()
        # Close connections opened while Playwright's loop is running too.
        connections.close_all()
    connections.close_all()


def login(page, live_server, username):
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(str(live_server) + "/login/")
    page.get_by_label("Login identifier").fill(username)
    page.get_by_label("Password", exact=True).fill(TEST_PASSWORD)
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.wait_for_url(str(live_server) + "/")
    expect(page.get_by_role("heading", name="Overview", exact=True)).to_be_visible()


def screenshot(page, name):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    page.evaluate("document.fonts.ready")
    assert page.evaluate("document.fonts.check('16px \"IBM Plex Sans\"')")
    page.screenshot(path=str(EVIDENCE / f"{name}.png"), full_page=True)


def shell_checks(page):
    assert page.locator(".app-header").bounding_box()["height"] == 48
    assert page.locator(".sidebar").bounding_box()["width"] == 240
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator('a[href="#"]').count() == 0
    assert page.locator(".sidebar").get_by_role("link", name="My tasks", exact=True).count() == (
        page.locator(".header-role").inner_text() == "Employee"
    )
    for cell in page.locator("th.numeric, td.numeric").all():
        assert cell.evaluate("el => getComputedStyle(el).textAlign") == "right"


def test_admin_account_journey_and_design(page, live_server, demo):
    login(page, live_server, "admin@demo.local")
    shell_checks(page)
    screenshot(page, "admin-overview")
    assert page.locator(".metric").nth(1).inner_text().split() == ["Projects", "4"]
    page.get_by_role("link", name="Employees", exact=True).click()
    expect(page.get_by_role("heading", name="Employees", exact=True)).to_be_visible()
    screenshot(page, "admin-employees")
    assert page.get_by_role("link", name="Activate", exact=True).count() == 0
    page.get_by_label("Search accounts").fill("no-account-matches")
    page.get_by_role("button", name="Search", exact=True).click()
    expect(page.get_by_text("No accounts match these filters.", exact=False)).to_be_visible()
    screenshot(page, "admin-no-results")
    page.get_by_role("link", name="Clear filters", exact=True).click()
    page.get_by_role("link", name="Create employee", exact=True).click()
    page.get_by_label("First name").fill("Browser")
    page.get_by_label("Last name").fill("Employee")
    page.get_by_label("Login identifier").fill("browser.employee")
    page.get_by_label("Initial password", exact=False).fill("Browser-Initial!582")
    screenshot(page, "admin-create-employee")
    page.get_by_role("button", name="Create employee", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Account created")
    account = User.objects.get(username="browser.employee")
    assert account.must_change_password and account.check_password("Browser-Initial!582")
    row = page.get_by_role("row").filter(has_text="browser.employee")
    row.get_by_role("link", name="Edit browser.employee", exact=True).click()
    page.get_by_label("First name").fill("Browser edited")
    screenshot(page, "admin-edit-employee")
    page.get_by_role("button", name="Save employee", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Account saved")
    account.refresh_from_db()
    assert account.first_name == "Browser edited"
    page.get_by_role("row").filter(has_text="browser.employee").get_by_role(
        "link", name="Deactivate browser.employee", exact=True
    ).click()
    expect(
        page.get_by_text("Projects, tasks and recorded time are preserved.", exact=False)
    ).to_be_visible()
    screenshot(page, "admin-deactivate-confirmation")
    page.get_by_label("I confirm this action.").check()
    page.get_by_role("button", name="Deactivate account", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Account deactivated")
    account.refresh_from_db()
    assert not account.is_active
    page.get_by_role("link", name="Projects", exact=True).click()
    page.get_by_role("link", name="Create project", exact=True).click()
    expect(page.get_by_label("Project manager")).to_be_visible()
    screenshot(page, "admin-project-form")


def test_manager_project_team_journey_and_keyboard(page, live_server, demo):
    login(page, live_server, "neha@demo.local")
    shell_checks(page)
    screenshot(page, "manager-overview")
    page.keyboard.press("Tab")
    expect(page.get_by_role("link", name="Skip to content")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#main")).to_be_focused()
    page.get_by_role("link", name="Projects", exact=True).click()
    screenshot(page, "manager-projects")
    page.get_by_role("link", name="Create project", exact=True).click()
    page.get_by_label("Project name").focus()
    page.keyboard.type("Browser project")
    page.keyboard.press("Tab")
    expect(page.get_by_label("Description")).to_be_focused()
    assert (
        page.get_by_label("Description").evaluate("el => getComputedStyle(el).outlineStyle")
        == "solid"
    )
    page.keyboard.type("A keyboard-entered project description.")
    page.get_by_label("Start date").fill("2026-10-06")
    page.get_by_label("End date").fill("2026-10-05")
    page.get_by_role("button", name="Create project", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("End date must be on or after")
    expect(page.get_by_label("Project name")).to_have_value("Browser project")
    expect(page.get_by_label("Description")).to_have_value(
        "A keyboard-entered project description."
    )
    screenshot(page, "manager-project-validation")
    page.get_by_label("End date").fill("2026-10-23")
    page.get_by_role("button", name="Create project", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Project created")
    project = Project.objects.get(name="Browser project")
    assert project.manager.username == "neha@demo.local"
    page.get_by_role("link", name="Browser project", exact=True).click()
    page.get_by_role("link", name="Edit project", exact=True).click()
    page.get_by_label("Project name").fill("Browser project edited")
    screenshot(page, "manager-edit-project")
    page.get_by_role("button", name="Save project", exact=True).click()
    expect(page.get_by_role("heading", name="Browser project edited", exact=True)).to_be_visible()
    page.get_by_role("link", name="Team", exact=True).click()
    page.get_by_role("link", name="Add employee", exact=True).click()
    page.get_by_label("Employee", exact=False).select_option(label="Dev Rao")
    screenshot(page, "manager-add-member")
    page.get_by_role("button", name="Add employee", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Employee added")
    dev = User.objects.get(username="dev@demo.local")
    assert ProjectMembership.objects.filter(project=project, employee=dev).exists()
    page.get_by_role("link", name="Remove Dev Rao", exact=True).click()
    page.get_by_label("I confirm this action.").check()
    page.get_by_role("button", name="Remove employee", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Employee removed")
    assert not ProjectMembership.objects.filter(project=project, employee=dev).exists()
    page.goto(str(live_server) + f"/projects/{demo.pk}/")
    screenshot(page, "manager-project-overview")
    page.get_by_role("link", name="Team", exact=True).click()
    screenshot(page, "manager-project-team")
    page.get_by_role("link", name="Remove Asha Deshmukh", exact=True).click()
    page.get_by_label("I confirm this action.").check()
    page.get_by_role("button", name="Remove employee", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Reassign or complete unfinished tasks")
    screenshot(page, "manager-member-removal-blocked")
    page.goto(str(live_server) + f"/projects/{demo.pk}/report/")
    shell_checks(page)
    screenshot(page, "manager-project-report")
    empty = Project.objects.get(demo_key="knowledge-base")
    page.goto(str(live_server) + f"/projects/{empty.pk}/report/")
    expect(page.get_by_text("No tasks yet", exact=True)).to_be_visible()
    expect(page.locator(".metric").nth(2)).to_contain_text("0%")
    screenshot(page, "manager-empty-report")
    # 720x450 CSS pixels at DPR 2 gives the same reflow/physical dimensions as 200% desktop zoom.
    zoom = page.context.browser.new_context(
        viewport={"width": 720, "height": 450},
        device_scale_factor=2,
        storage_state=page.context.storage_state(),
    )
    zoom_page = zoom.new_page()
    zoom_page.goto(str(live_server) + f"/projects/{demo.pk}/report/")
    assert zoom_page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    expect(zoom_page.get_by_role("link", name="Edit project", exact=True)).to_be_visible()
    screenshot(zoom_page, "manager-report-200-percent")
    zoom_page.goto(str(live_server) + f"/projects/{demo.pk}/edit/")
    expect(zoom_page.get_by_label("Project name")).to_be_visible()
    screenshot(zoom_page, "manager-project-form-200-percent")
    zoom.close()
    page.goto(str(live_server) + "/password/change/")
    expect(page.get_by_role("heading", name="Change password", exact=True)).to_be_visible()
    screenshot(page, "password-change")


def test_employee_readonly_and_foreign_access(page, live_server, demo):
    login(page, live_server, "asha@demo.local")
    shell_checks(page)
    screenshot(page, "employee-overview")
    page.goto(str(live_server) + f"/projects/{demo.pk}/")
    screenshot(page, "employee-project-overview")
    for section in ["", "team/", "report/"]:
        page.goto(str(live_server) + f"/projects/{demo.pk}/" + section)
        assert page.get_by_role("link", name="Edit project", exact=True).count() == 0
        assert page.get_by_role("link", name="Add employee", exact=True).count() == 0
        assert page.get_by_role("link", name="Remove", exact=False).count() == 0
    expect(page.get_by_text("Own work.", exact=False).first).to_be_visible()
    screenshot(page, "employee-project-report")
    foreign = Project.objects.get(demo_key="operations-handbook")
    response = page.goto(str(live_server) + f"/projects/{foreign.pk}/")
    assert response.status == 404
    # DEBUG=False exercises the intentionally generic unavailable page.
    django_settings.DEBUG = False
    response = page.goto(str(live_server) + f"/projects/{foreign.pk}/")
    assert response.status == 404 and "Operations Handbook" not in page.content()
    screenshot(page, "employee-unavailable")
    django_settings.DEBUG = True
    page.goto(str(live_server) + "/")
    page.get_by_role("button", name="Sign out", exact=True).click()
    login(page, live_server, "arjun@demo.local")
    response = page.goto(str(live_server) + f"/projects/{demo.pk}/")
    assert response.status == 404

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.test import Client
from django.utils import timezone

from accounts.models import User
from projects import services
from projects.models import Project, ProjectMembership

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace():
    users = {}
    for name, role in [
        ("admin", "ADMIN"),
        ("manager", "PROJECT_MANAGER"),
        ("foreign", "PROJECT_MANAGER"),
        ("employee", "EMPLOYEE"),
        ("colleague", "EMPLOYEE"),
        ("outsider", "EMPLOYEE"),
    ]:
        users[name] = User.objects.create_user(
            username=name, first_name=name.title(), role=role, must_change_password=False
        )
    t = SimpleNamespace(**users)
    t.today = timezone.localdate()
    t.project = services.create_project(
        t.manager, name="Visible project", start_date=t.today, end_date=t.today
    )
    t.other = services.create_project(
        t.foreign, name="Foreign secret", start_date=t.today, end_date=t.today
    )
    t.empty = services.create_project(
        t.manager, name="Empty project", start_date=t.today, end_date=t.today
    )
    services.add_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    t.task = services.create_task(
        t.manager, t.project.pk, title="Visible task", assignee_id=t.employee.pk
    )
    services.update_task(t.employee, t.task.pk, status="IN_PROGRESS")
    t.entry = services.create_time_entry(
        t.employee, t.task.pk, work_date=t.today, minutes=90, note="Private work note"
    )
    return t


def client_for(user):
    client = Client()
    client.force_login(user)
    return client


def project_data(t, **extra):
    return {
        "name": "Edited project",
        "description": "Preserve this text",
        "start_date": str(t.today),
        "end_date": str(t.today),
        **extra,
    }


def account_data(t, **extra):
    return {
        "first_name": "Created",
        "last_name": "Employee",
        "username": "created",
        "email": "",
        "role": "EMPLOYEE",
        "password": "Initial-Private!793",
        **extra,
    }


@pytest.mark.parametrize("role", ["admin", "manager", "employee"])
def test_real_overviews_and_navigation(workspace, role):
    t = workspace
    response = client_for(getattr(t, role)).get("/")
    assert response.status_code == 200
    summary = response.context["summary"]
    assert summary["project_count"] == {"admin": 3, "manager": 2, "employee": 1}[role]
    assert summary["total_minutes"] == 90
    html = response.content.decode()
    assert f'href="/tasks/{t.task.pk}/"' in html and 'href="#"' not in html
    assert 'aria-current="page"' in html and 'method="post" action="/logout/"' in html
    assert ('href="/employees/"' in html) == (role == "admin")


@pytest.mark.parametrize("role", ["manager", "employee"])
def test_project_search_and_direct_scope(workspace, role):
    t = workspace
    client = client_for(getattr(t, role))
    response = client.get("/projects/?q=Foreign")
    assert response.status_code == 200
    assert "Foreign secret" not in response.content.decode()
    assert "No projects match" in response.content.decode()
    for section in ["", "team/", "report/", "edit/", "team/add/"]:
        response = client.get(f"/projects/{t.other.pk}/" + section)
        assert response.status_code in {403, 404}
        assert "Foreign secret" not in response.content.decode()
    assert client.post(f"/projects/{t.other.pk}/edit/", project_data(t)).status_code in {403, 404}


def test_unrelated_employee_denied_and_read_only_member(workspace):
    t = workspace
    client = client_for(t.employee)
    for section in ["", "team/", "report/"]:
        response = client.get(f"/projects/{t.project.pk}/" + section)
        assert response.status_code == 200
        html = response.content.decode()
        for text in ["Edit project", "Add employee", "Remove<span", "Private work note"]:
            assert text not in html
        if section != "team/":
            assert "Own work" in html
        assert client_for(t.outsider).get(f"/projects/{t.project.pk}/" + section).status_code == 404
    assert (
        client.post(
            f"/projects/{t.project.pk}/team/add/", {"employee_id": t.colleague.pk}
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/projects/{t.project.pk}/team/{t.employee.pk}/remove/", {"confirm": "on"}
        ).status_code
        == 403
    )
    assert client.get("/projects/create/").status_code == 403


@pytest.mark.parametrize("role", ["manager", "employee"])
def test_account_pages_and_actions_admin_only(workspace, role):
    t = workspace
    client = client_for(getattr(t, role))
    for url in [
        "/employees/",
        "/employees/create/",
        f"/employees/{t.employee.pk}/edit/",
        f"/employees/{t.employee.pk}/deactivate/",
    ]:
        assert client.get(url).status_code == 403
        assert client.post(url, account_data(t)).status_code in {403, 405}


def test_manager_create_edit_member_add_and_remove(workspace):
    t = workspace
    client = client_for(t.manager)
    assert client.post("/projects/create/", project_data(t, name="New project")).status_code == 302
    project = Project.objects.get(name="New project")
    assert project.manager_id == t.manager.pk
    assert client.post(f"/projects/{project.pk}/edit/", project_data(t)).status_code == 302
    assert (
        client.post(
            f"/projects/{project.pk}/team/add/", {"employee_id": t.colleague.pk}
        ).status_code
        == 302
    )
    member = ProjectMembership.objects.get(project=project, employee=t.colleague)
    assert client.get(f"/projects/{project.pk}/team/{t.colleague.pk}/remove/").status_code == 200
    assert ProjectMembership.objects.filter(pk=member.pk).exists()
    assert (
        client.post(
            f"/projects/{project.pk}/team/{t.colleague.pk}/remove/", {"confirm": "on"}
        ).status_code
        == 302
    )
    assert not ProjectMembership.objects.filter(pk=member.pk).exists()


def test_project_dates_and_forgery_preserve_input(workspace):
    t = workspace
    client = client_for(t.manager)
    response = client.post("/projects/create/", project_data(t, end_date="2000-01-01"))
    assert (
        response.status_code == 200 and "End date must be on or after" in response.content.decode()
    )
    assert response.context["form"]["description"].value() == "Preserve this text"
    response = client.post("/projects/create/", project_data(t, manager_id=t.foreign.pk))
    assert "cannot be changed" in response.content.decode()
    assert not Project.objects.filter(name="Edited project").exists()


def test_admin_manager_selector_create_and_change_owner(workspace):
    t = workspace
    client = client_for(t.admin)
    assert not t.admin.is_staff and not t.admin.is_superuser
    response = client.get("/projects/create/")
    assert "manager_id" in response.context["form"].fields
    assert (
        client.post(
            "/projects/create/", project_data(t, name="Admin owned choice", manager_id=t.foreign.pk)
        ).status_code
        == 302
    )
    assert Project.objects.get(name="Admin owned choice").manager_id == t.foreign.pk
    assert (
        client.post(
            f"/projects/{t.project.pk}/edit/", project_data(t, manager_id=t.foreign.pk)
        ).status_code
        == 302
    )
    assert client_for(t.manager).get(f"/projects/{t.project.pk}/").status_code == 404


def test_account_create_edit_reset_and_deactivation(workspace):
    t = workspace
    client = client_for(t.admin)
    assert client.post("/employees/create/", account_data(t)).status_code == 302
    user = User.objects.get(username="created")
    assert user.check_password("Initial-Private!793") and user.must_change_password
    old_hash = user.password
    assert (
        client.post(
            f"/employees/{user.pk}/edit/",
            account_data(t, username=user.username, first_name="Edited", password=""),
        ).status_code
        == 302
    )
    user.refresh_from_db()
    assert user.first_name == "Edited" and user.password == old_hash
    assert (
        client.post(
            f"/employees/{user.pk}/edit/",
            account_data(t, username=user.username, password="Reset-Private!784"),
        ).status_code
        == 302
    )
    user.refresh_from_db()
    assert user.check_password("Reset-Private!784") and user.must_change_password
    assert client.get(f"/employees/{user.pk}/deactivate/").status_code == 200
    user.refresh_from_db()
    assert user.is_active
    assert client.post(f"/employees/{user.pk}/deactivate/", {"confirm": "on"}).status_code == 302
    assert (
        client.post(f"/employees/{t.employee.pk}/deactivate/", {"confirm": "on"}).status_code == 302
    )
    t.entry.refresh_from_db()
    assert t.entry.employee_id == t.employee.pk and t.entry.minutes == 90


def test_account_error_clears_password_and_confirms_role(workspace):
    t = workspace
    client = client_for(t.admin)
    response = client.post("/employees/create/", account_data(t, username=t.employee.username))
    assert response.status_code == 200 and response.context["form"].errors
    assert "Initial-Private!793" not in response.content.decode()
    assert response.context["form"]["first_name"].value() == "Created"
    response = client.post(
        f"/employees/{t.outsider.pk}/edit/",
        account_data(t, username=t.outsider.username, role="PROJECT_MANAGER", password=""),
    )
    assert "Confirm the role change" in response.content.decode()
    response = client.post(
        f"/employees/{t.outsider.pk}/edit/",
        account_data(
            t, username=t.outsider.username, role="PROJECT_MANAGER", password="", confirm_role="on"
        ),
    )
    assert response.status_code == 302
    response = client.post(
        f"/employees/{t.manager.pk}/edit/",
        account_data(
            t, username=t.manager.username, role="EMPLOYEE", password="", confirm_role="on"
        ),
    )
    assert "Reassign owned projects" in response.content.decode()


def test_account_search_no_activation_and_protected_fields(workspace):
    t = workspace
    client = client_for(t.admin)
    response = client.get("/employees/?q=Colleague")
    assert list(response.context["page"]) == [t.colleague]
    assert "Activate" not in response.content.decode()
    response = client.post("/employees/create/", account_data(t, is_superuser="on"))
    assert response.context["form"].errors and not User.objects.filter(username="created").exists()


def test_membership_rejections_and_get_never_mutates(workspace):
    t = workspace
    client = client_for(t.manager)
    response = client.post(f"/projects/{t.project.pk}/team/add/", {"employee_id": t.employee.pk})
    assert response.status_code == 200 and response.context["form"].errors
    response = client.post(
        f"/projects/{t.project.pk}/team/{t.employee.pk}/remove/", {"confirm": "on"}
    )
    assert "Reassign or complete unfinished tasks" in response.content.decode()
    assert ProjectMembership.objects.filter(project=t.project, employee=t.employee).exists()
    assert (
        client.post(f"/projects/{t.empty.pk}/team/add/", {"employee_id": t.foreign.pk})
        .context["form"]
        .errors
    )


def test_failed_save_state_preserves_nonsecret_input(workspace):
    t = workspace
    with patch("projects.services.update_project", side_effect=DatabaseError("Test outage")):
        response = client_for(t.manager).post(f"/projects/{t.project.pk}/edit/", project_data(t))
    assert "Your changes could not be saved. Try again." in response.content.decode()
    assert response.context["form"]["description"].value() == "Preserve this text"
    t.project.refresh_from_db()
    assert t.project.name == "Visible project"


def test_empty_projects_and_readable_report(workspace):
    t = workspace
    client = client_for(t.manager)
    response = client.get("/projects/")
    assert (
        "Empty project" in response.content.decode() and "No tasks yet" in response.content.decode()
    )
    response = client.get(f"/projects/{t.project.pk}/report/")
    assert "1h 30m" in response.content.decode() and 'class="numeric"' in response.content.decode()
    assert "Private work note" not in response.content.decode()


def test_html_csrf_and_unsupported_methods(workspace):
    t = workspace
    client = Client(enforce_csrf_checks=True)
    client.force_login(t.manager)
    assert client.post("/projects/create/", project_data(t)).status_code == 403
    client.get("/projects/create/")
    token = client.cookies["csrftoken"].value
    assert (
        client.post("/projects/create/", project_data(t, csrfmiddlewaretoken=token)).status_code
        == 302
    )
    assert client.put(f"/projects/{t.project.pk}/edit/", HTTP_X_CSRFTOKEN=token).status_code == 405
    assert (
        client.delete(
            f"/projects/{t.project.pk}/team/{t.employee.pk}/remove/", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 405
    )

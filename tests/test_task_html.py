"""Task/time HTML permissions and workflows against PostgreSQL fixtures."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.test import Client

from accounts.services import deactivate_account, update_account
from projects import services
from projects.models import Task, TimeEntry
from tests.test_workspace_html import client_for
from tests.test_workspace_html import workspace as workspace

pytestmark = pytest.mark.django_db


def task_data(t, **extra):
    return {
        "title": "New task",
        "description": "Retained task text",
        "assignee_id": t.employee.pk,
        **extra,
    }


def time_data(t, **extra):
    return {"work_date": str(t.today), "minutes": 60, "note": "Retained private note", **extra}


def test_complete_html_journey(workspace):
    t = workspace
    manager, employee = client_for(t.manager), client_for(t.employee)
    assert manager.post(f"/projects/{t.project.pk}/tasks/create/", task_data(t)).status_code == 302
    task = Task.objects.get(title="New task")
    assert employee.get(f"/tasks/{task.pk}/start/").status_code == 405
    assert employee.post(f"/tasks/{task.pk}/start/").status_code == 302
    assert employee.post(f"/tasks/{task.pk}/time/add/", time_data(t)).status_code == 302
    entry = TimeEntry.objects.get(task=task)
    assert (
        employee.post(f"/time-entries/{entry.pk}/edit/", time_data(t, minutes=90)).status_code
        == 302
    )
    assert employee.get(f"/tasks/{task.pk}/complete/").status_code == 200
    task.refresh_from_db()
    assert task.status == "IN_PROGRESS"
    assert employee.post(f"/tasks/{task.pk}/complete/", {"confirm": "on"}).status_code == 302
    task.refresh_from_db()
    assert task.status == "COMPLETED"
    assert (
        manager.get(f"/projects/{t.project.pk}/report/").context["report"]["total_minutes"] == 180
    )
    assert employee.post(f"/tasks/{task.pk}/complete/", {"confirm": "on"}).status_code == 302


@pytest.mark.parametrize("role", ["foreign", "outsider"])
def test_foreign_task_and_time_urls_unavailable(workspace, role):
    t = workspace
    client = client_for(getattr(t, role))
    for url in [
        f"/projects/{t.project.pk}/tasks/",
        f"/projects/{t.project.pk}/tasks/create/",
        f"/tasks/{t.task.pk}/",
        f"/tasks/{t.task.pk}/edit/",
        f"/tasks/{t.task.pk}/start/",
        f"/tasks/{t.task.pk}/complete/",
        f"/tasks/{t.task.pk}/delete/",
        f"/tasks/{t.task.pk}/time/add/",
        f"/time-entries/{t.entry.pk}/edit/",
        f"/time-entries/{t.entry.pk}/delete/",
        f"/time-entries/{t.entry.pk}/correction/",
    ]:
        assert client.get(url).status_code in {404, 405}
        assert client.post(url, {}).status_code in {404, 405}


def test_team_employee_reads_without_private_notes_or_actions(workspace):
    t = workspace
    services.add_member(t.manager, t.project.pk, employee_id=t.colleague.pk)
    client = client_for(t.colleague)
    response = client.get(f"/tasks/{t.task.pk}/")
    html = response.content.decode()
    assert response.status_code == 200 and "Private work note" not in html
    assert (
        "Edit task" not in html and "Log time</button>" not in html and "Mark completed" not in html
    )
    for action in ["start", "complete", "edit", "delete"]:
        assert client.post(f"/tasks/{t.task.pk}/{action}/", {"confirm": "on"}).status_code == 403
    assert client.get(f"/time-entries/{t.entry.pk}/edit/").status_code == 404
    assert client.post(f"/tasks/{t.task.pk}/time/add/", time_data(t)).status_code == 403
    assert (
        "Private work note" not in client.get(f"/projects/{t.project.pk}/tasks/").content.decode()
    )


def test_scoped_filters_and_default_unfinished(workspace):
    t = workspace
    services.update_task(t.employee, t.task.pk, status="COMPLETED")
    client = client_for(t.employee)
    assert not client.get("/my-tasks/").context["task_rows"]
    assert len(client.get("/my-tasks/?status=COMPLETED").context["task_rows"]) == 1
    response = client.get(f"/my-tasks/?project={t.other.pk}&status=")
    assert response.status_code == 400 and "Foreign secret" not in response.content.decode()
    manager = client_for(t.manager)
    assert manager.get("/my-tasks/").status_code == 403
    response = manager.get(f"/projects/{t.project.pk}/tasks/?assignee={t.outsider.pk}")
    assert response.status_code == 400 and not response.context["task_rows"]
    assert not manager.get(f"/projects/{t.project.pk}/tasks/?status=TODO").context["task_rows"]
    services.add_member(t.manager, t.project.pk, employee_id=t.colleague.pk)
    response = manager.get(f"/projects/{t.project.pk}/tasks/?assignee={t.colleague.pk}")
    assert response.status_code == 200 and not response.context["task_rows"]


@pytest.mark.parametrize(
    "extra", [{"project_id": 999}, {"status": "COMPLETED"}, {"employee_id": 999}]
)
def test_task_protected_fields_rejected(workspace, extra):
    t = workspace
    response = client_for(t.manager).post(
        f"/projects/{t.project.pk}/tasks/create/", task_data(t, **extra)
    )
    assert response.context["form"].errors and not Task.objects.filter(title="New task").exists()
    assert response.context["form"]["description"].value() == "Retained task text"


def test_assignment_errors_and_empty_member_guidance(workspace):
    t = workspace
    client = client_for(t.manager)
    response = client.post(
        f"/projects/{t.project.pk}/tasks/create/", task_data(t, assignee_id=t.outsider.pk)
    )
    assert "assignee_id" in response.context["form"].errors
    response = client.get(f"/projects/{t.empty.pk}/tasks/create/")
    assert "No eligible members" in response.content.decode()
    assert client_for(t.employee).get(f"/projects/{t.project.pk}/tasks/create/").status_code == 403


@pytest.mark.parametrize("minutes", ["0", "1441", "1.5", "true"])
def test_invalid_minutes_keep_date_and_note(workspace, minutes):
    t = workspace
    response = client_for(t.employee).post(
        f"/tasks/{t.task.pk}/time/add/", time_data(t, minutes=minutes)
    )
    assert response.context["form"].errors
    assert response.context["form"]["note"].value() == "Retained private note"
    assert TimeEntry.objects.filter(task=t.task).count() == 1


def test_future_dates_and_time_identity_forgery(workspace):
    t = workspace
    client = client_for(t.employee)
    for extra in [
        {"work_date": str(t.today + timedelta(days=1))},
        {"employee_id": t.colleague.pk},
        {"task_id": t.task.pk},
    ]:
        response = client.post(f"/tasks/{t.task.pk}/time/add/", time_data(t, **extra))
        assert response.context["form"].errors
    assert TimeEntry.objects.filter(task=t.task).count() == 1


def test_time_delete_confirmation_and_protected_task_delete(workspace):
    t = workspace
    client = client_for(t.employee)
    assert client.get(f"/time-entries/{t.entry.pk}/delete/").status_code == 200
    assert TimeEntry.objects.filter(pk=t.entry.pk).exists()
    assert client.post(f"/time-entries/{t.entry.pk}/delete/", {}).context["form"].errors
    response = client_for(t.manager).post(f"/tasks/{t.task.pk}/delete/", {"confirm": "on"})
    assert "history must be preserved" in response.content.decode()
    assert client.post(f"/time-entries/{t.entry.pk}/delete/", {"confirm": "on"}).status_code == 302
    assert (
        client_for(t.manager).post(f"/tasks/{t.task.pk}/delete/", {"confirm": "on"}).status_code
        == 302
    )
    assert not Task.objects.filter(pk=t.task.pk).exists()


def test_completed_actions_and_stale_forms(workspace):
    t = workspace
    employee, manager = client_for(t.employee), client_for(t.manager)
    assert employee.get(f"/time-entries/{t.entry.pk}/edit/").status_code == 200
    services.update_task(t.employee, t.task.pk, status="COMPLETED")
    for client in [employee, manager]:
        html = client.get(f"/tasks/{t.task.pk}/").content.decode()
        assert "Completed and read-only" in html
        assert (
            "Edit task" not in html and "Delete task" not in html and "Mark completed" not in html
        )
    assert manager.get(f"/tasks/{t.task.pk}/edit/").status_code == 403
    response = manager.post(f"/tasks/{t.task.pk}/edit/", task_data(t))
    assert response.status_code == 403 and response.context["form"]["title"].value() == "New task"
    response = employee.post(f"/time-entries/{t.entry.pk}/edit/", time_data(t))
    assert (
        response.status_code == 403
        and response.context["form"]["note"].value() == "Retained private note"
    )
    assert (
        employee.post(f"/time-entries/{t.entry.pk}/delete/", {"confirm": "on"}).status_code == 403
    )
    t.entry.refresh_from_db()
    assert t.entry.minutes == 90


def test_reassignment_and_admin_corrections_preserve_attribution(workspace):
    t = workspace
    services.add_member(t.manager, t.project.pk, employee_id=t.colleague.pk)
    client = client_for(t.manager)
    assert (
        client.post(
            f"/tasks/{t.task.pk}/edit/", task_data(t, assignee_id=t.colleague.pk)
        ).status_code
        == 302
    )
    assert (
        client_for(t.employee).post(f"/time-entries/{t.entry.pk}/edit/", time_data(t)).status_code
        == 403
    )
    assert client_for(t.colleague).get(f"/tasks/{t.task.pk}/").context["total_minutes"] == 0
    services.update_task(t.colleague, t.task.pk, status="COMPLETED")
    admin = client_for(t.admin)
    assert admin.post(f"/tasks/{t.task.pk}/correction/", task_data(t)).status_code == 302
    assert (
        admin.post(f"/time-entries/{t.entry.pk}/correction/", time_data(t, minutes=120)).status_code
        == 302
    )
    t.task.refresh_from_db()
    t.entry.refresh_from_db()
    assert (
        t.task.status == "COMPLETED"
        and t.entry.employee_id == t.employee.pk
        and t.entry.task_id == t.task.pk
        and t.entry.minutes == 120
    )
    for actor in [t.manager, t.employee]:
        assert (
            client_for(actor).post(f"/tasks/{t.task.pk}/correction/", task_data(t)).status_code
            == 403
        )
        assert (
            client_for(actor)
            .post(f"/time-entries/{t.entry.pk}/correction/", time_data(t))
            .status_code
            == 403
        )
    assert client.post(f"/time-entries/{t.entry.pk}/edit/", time_data(t)).status_code == 403


def test_historical_assignee_retained_without_eligible_options(workspace):
    t = workspace
    services.update_task(t.employee, t.task.pk, status="COMPLETED")
    services.remove_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    response = client_for(t.admin).post(
        f"/tasks/{t.task.pk}/correction/", task_data(t, assignee_id="")
    )
    assert response.status_code == 302
    t.task.refresh_from_db()
    assert t.task.assignee_id == t.employee.pk and t.task.status == "COMPLETED"


def test_database_failure_preserves_time_input(workspace):
    t = workspace
    with patch("projects.services.create_time_entry", side_effect=DatabaseError("Test outage")):
        response = client_for(t.employee).post(f"/tasks/{t.task.pk}/time/add/", time_data(t))
    assert "Your changes could not be saved" in response.content.decode()
    assert response.context["form"]["minutes"].value() == "60"


def test_actual_csrf_task_and_time_mutations(workspace):
    t = workspace
    client = Client(enforce_csrf_checks=True)
    client.force_login(t.employee)
    assert client.post(f"/tasks/{t.task.pk}/time/add/", time_data(t)).status_code == 403
    client.get(f"/tasks/{t.task.pk}/")
    token = client.cookies["csrftoken"].value
    assert (
        client.post(
            f"/tasks/{t.task.pk}/time/add/", time_data(t, csrfmiddlewaretoken=token)
        ).status_code
        == 302
    )

    assert client.post(f"/tasks/{t.task.pk}/complete/", {"confirm": "on"}).status_code == 403
    assert (
        client.post(
            f"/tasks/{t.task.pk}/complete/", {"confirm": "on", "csrfmiddlewaretoken": token}
        ).status_code
        == 302
    )


def test_task_pagination_preserves_scoped_filters(workspace):
    t = workspace
    for n in range(27):
        services.create_task(
            t.manager, t.project.pk, title=f"Page task {n}", assignee_id=t.employee.pk
        )
    query = f"status=TODO&assignee={t.employee.pk}"
    response = client_for(t.manager).get(f"/projects/{t.project.pk}/tasks/?{query}")
    assert len(response.context["task_rows"]) == 25
    assert f"status=TODO&amp;assignee={t.employee.pk}&amp;page=2" in response.content.decode()
    response = client_for(t.manager).get(f"/projects/{t.project.pk}/tasks/?{query}&page=2")
    assert len(response.context["task_rows"]) == 2
    assert [row["task"].title for row in response.context["task_rows"]] == [
        "Page task 25",
        "Page task 26",
    ]


def test_password_gate_and_inactive_session_cover_task_routes(workspace):
    t = workspace
    client = client_for(t.employee)
    update_account(t.admin, t.employee.pk, password="Replacement-Private!652")
    t.employee.refresh_from_db()
    client.force_login(t.employee)
    assert client.get(f"/tasks/{t.task.pk}/").url.startswith("/password/change/")
    assert client.post(f"/tasks/{t.task.pk}/time/add/", time_data(t)).status_code == 302
    deactivate_account(t.admin, t.employee.pk)
    response = client.get("/my-tasks/")
    assert response.status_code == 302 and response.url.startswith("/login/")

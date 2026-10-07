from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from projects import services
from projects.models import Project, Task
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def world():
    users = {}
    for name, role in [
        ("admin", User.Role.ADMIN),
        ("manager", User.Role.PROJECT_MANAGER),
        ("foreign", User.Role.PROJECT_MANAGER),
        ("employee", User.Role.EMPLOYEE),
        ("colleague", User.Role.EMPLOYEE),
        ("outsider", User.Role.EMPLOYEE),
    ]:
        users[name] = User.objects.create_user(name, role=role, must_change_password=False)
    t = SimpleNamespace(**users)
    t.today = timezone.localdate()
    t.project = services.create_project(
        t.manager, name="Delivery", start_date=t.today, end_date=t.today
    )
    t.other = services.create_project(
        t.foreign, name="Foreign", start_date=t.today, end_date=t.today
    )
    services.add_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    services.add_member(t.manager, t.project.pk, employee_id=t.colleague.pk)
    t.task = services.create_task(t.manager, t.project.pk, title="Build", assignee_id=t.employee.pk)
    t.foreign_task = services.create_task(
        t.foreign, t.other.pk, title="Foreign work", assignee_id=_add_foreign_member(t)
    )
    return t


def _add_foreign_member(t):
    services.add_member(t.foreign, t.other.pk, employee_id=t.outsider.pk)
    return t.outsider.pk


def api(user):
    client = APIClient()
    client.force_login(user)
    return client


def time_entry(t, user=None, task=None, minutes=60, note="Private note"):
    user, task = user or t.employee, task or t.task
    if task.status == Task.Status.TODO:
        task = services.update_task(user, task.pk, status=Task.Status.IN_PROGRESS)
    return services.create_time_entry(user, task.pk, work_date=t.today, minutes=minutes, note=note)


def test_http_complete_journey(world):
    t = world
    assert connection.vendor == "postgresql"
    manager, employee = api(t.manager), api(t.employee)
    response = manager.post(
        "/api/projects/",
        {"name": "HTTP", "start_date": str(t.today), "end_date": str(t.today)},
        format="json",
    )
    assert response.status_code == 201
    project = response.json()["id"]
    assert response.json()["manager_id"] == t.manager.pk
    assert (
        manager.post(
            f"/api/projects/{project}/memberships/", {"employee_id": t.employee.pk}, format="json"
        ).status_code
        == 201
    )
    response = manager.post(
        "/api/tasks/",
        {"project_id": project, "title": "HTTP task", "assignee_id": t.employee.pk},
        format="json",
    )
    assert response.status_code == 201
    task = response.json()["id"]
    assert response.json()["status"] == "TODO"
    assert (
        employee.patch(f"/api/tasks/{task}/", {"status": "IN_PROGRESS"}, format="json").status_code
        == 200
    )
    response = employee.post(
        "/api/time-entries/",
        {"task_id": task, "work_date": str(t.today), "minutes": 45, "note": "Done"},
        format="json",
    )
    assert response.status_code == 201 and response.json()["employee_id"] == t.employee.pk
    assert (
        employee.patch(f"/api/tasks/{task}/", {"status": "COMPLETED"}, format="json").status_code
        == 200
    )
    report = manager.get(f"/api/projects/{project}/report/").json()
    assert report["completed_tasks"] == report["total_tasks"] == 1
    assert report["completion_percentage"] == 100 and report["total_minutes"] == 45


@pytest.mark.parametrize("who", ["foreign", "outsider"])
@pytest.mark.parametrize("route", ["project", "task", "memberships", "report", "picker", "time"])
def test_foreign_details_consistent_404(world, who, route):
    t = world
    entry = time_entry(t)
    urls = {
        "project": f"/api/projects/{t.project.pk}/",
        "task": f"/api/tasks/{t.task.pk}/",
        "memberships": f"/api/projects/{t.project.pk}/memberships/",
        "report": f"/api/projects/{t.project.pk}/report/",
        "picker": f"/api/projects/{t.project.pk}/employee-options/",
        "time": f"/api/time-entries/{entry.pk}/",
    }
    response = api(getattr(t, who)).get(urls[route])
    assert response.status_code == 404
    assert response.json() == {"detail": "Resource unavailable."}


@pytest.mark.parametrize("who", ["foreign", "outsider"])
def test_foreign_mutations_404(world, who):
    t = world
    client = api(getattr(t, who))
    entry = time_entry(t)
    for url, data in [
        (f"/api/projects/{t.project.pk}/", {"name": "Stolen"}),
        (f"/api/tasks/{t.task.pk}/", {"status": "COMPLETED"}),
        (f"/api/time-entries/{entry.pk}/", {"minutes": 1}),
    ]:
        assert client.patch(url, data, format="json").status_code == 404
    assert (
        client.post(
            f"/api/projects/{t.project.pk}/memberships/",
            {"employee_id": t.outsider.pk},
            format="json",
        ).status_code
        == 404
    )
    assert client.delete(f"/api/projects/{t.project.pk}/").status_code == 404


def test_scoped_lists_filters_and_overview(world):
    t = world
    time_entry(t, minutes=31)
    time_entry(t, t.outsider, t.foreign_task, minutes=900)
    for user in [t.manager, t.employee]:
        client = api(user)
        assert client.get("/api/projects/").json()["count"] == 1
        assert client.get("/api/tasks/").json()["count"] == 1
        assert client.get(f"/api/tasks/?project={t.other.pk}").json()["results"] == []
        assert client.get(f"/api/tasks/?assignee={t.outsider.pk}").json()["results"] == []
        assert client.get("/api/tasks/?status=COMPLETED").json()["count"] == 0
        assert (
            client.get(
                f"/api/tasks/?project={t.project.pk}&status=IN_PROGRESS&assignee={t.employee.pk}"
            ).json()["count"]
            == 1
        )
        assert client.get(f"/api/time-entries/?project={t.other.pk}").json()["count"] == 0
        assert client.get(f"/api/time-entries/?task={t.foreign_task.pk}").json()["count"] == 0
        summary = client.get("/api/overview/").json()
        assert summary["project_count"] == 1 and summary["total_minutes"] == 31
    assert api(t.admin).get("/api/overview/").json()["total_minutes"] == 931


@pytest.mark.parametrize("query", ["project=bad", "assignee=0", "status=DONE"])
def test_invalid_task_filters_400(world, query):
    assert api(world.manager).get("/api/tasks/?" + query).status_code == 400


def test_private_notes_and_nested_serialization(world):
    t = world
    mine = time_entry(t)
    colleague_task = services.create_task(
        t.manager, t.project.pk, title="Team task", assignee_id=t.colleague.pk
    )
    private = time_entry(t, t.colleague, colleague_task, note="Colleague confidential")
    employee = api(t.employee)
    assert employee.get("/api/time-entries/").json()["count"] == 1
    assert employee.get(f"/api/time-entries/{private.pk}/").status_code == 404
    assert (
        employee.patch(
            f"/api/time-entries/{private.pk}/", {"minutes": 1}, format="json"
        ).status_code
        == 404
    )
    assert employee.get(f"/api/time-entries/{mine.pk}/").json()["note"] == "Private note"
    for url in [
        "/api/projects/",
        "/api/tasks/",
        f"/api/tasks/{colleague_task.pk}/",
        f"/api/projects/{t.project.pk}/memberships/",
        f"/api/projects/{t.project.pk}/report/",
        "/api/overview/",
    ]:
        response = employee.get(url)
        assert response.status_code == 200
        text = response.content.decode()
        assert "Colleague confidential" not in text and "Private note" not in text
        assert "password" not in text and "is_staff" not in text and "is_superuser" not in text
    report = employee.get(f"/api/projects/{t.project.pk}/report/").json()
    assert report["scope"] == "own_work" and report["total_tasks"] == 1
    assert [row["employee_id"] for row in report["contributors"]] == [t.employee.pk]


@pytest.mark.parametrize("field", ["manager_id", "manager", "demo_key", "id", "role"])
def test_project_forgery_rejected(world, field):
    response = api(world.manager).patch(
        f"/api/projects/{world.project.pk}/", {field: world.foreign.pk}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize("field", ["project_id", "employee_id", "id"])
def test_task_forgery_rejected(world, field):
    assert (
        api(world.manager)
        .patch(f"/api/tasks/{world.task.pk}/", {field: world.other.pk}, format="json")
        .status_code
        == 400
    )


@pytest.mark.parametrize("minutes", [True, False, 1.5, 1.0, "60", 0, 1441, None])
def test_minutes_strict_json_and_bounds(world, minutes):
    t = world
    entry = time_entry(t)
    client = api(t.employee)
    assert (
        client.post(
            "/api/time-entries/",
            {"task_id": t.task.pk, "work_date": str(t.today), "minutes": minutes},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/time-entries/{entry.pk}/", {"minutes": minutes}, format="json"
        ).status_code
        == 400
    )
    entry.refresh_from_db()
    assert entry.minutes == 60


def test_partial_put_validation_and_readonly_fields(world):
    t = world
    manager = api(t.manager)
    assert (
        manager.patch(
            f"/api/projects/{t.project.pk}/", {"description": "Edited"}, format="json"
        ).status_code
        == 200
    )
    assert (
        manager.put(
            f"/api/projects/{t.project.pk}/", {"name": "PUT edit"}, format="json"
        ).status_code
        == 200
    )
    assert (
        manager.patch(
            f"/api/projects/{t.project.pk}/",
            {"end_date": str(t.today - timedelta(days=1))},
            format="json",
        ).status_code
        == 400
    )
    assert (
        manager.patch(f"/api/tasks/{t.task.pk}/", {"title": " "}, format="json").status_code == 400
    )
    assert (
        manager.patch(f"/api/tasks/{t.task.pk}/", {"status": "INVALID"}, format="json").status_code
        == 400
    )
    assert (
        manager.post("/api/tasks/", {"project_id": t.project.pk}, format="json").status_code == 400
    )
    assert manager.post("/api/projects/", {"name": "Missing"}, format="json").status_code == 400
    assert (
        manager.patch(
            f"/api/tasks/{t.task.pk}/", {"assignee_id": t.outsider.pk}, format="json"
        ).status_code
        == 400
    )
    assert (
        manager.post(
            f"/api/projects/{t.project.pk}/memberships/",
            {"employee_id": t.employee.pk},
            format="json",
        ).status_code
        == 400
    )
    assert (
        manager.delete(f"/api/projects/{t.project.pk}/memberships/{t.employee.pk}/").status_code
        == 400
    )
    entry = time_entry(t)
    employee = api(t.employee)
    assert (
        employee.patch(
            f"/api/tasks/{t.task.pk}/", {"title": "Not allowed"}, format="json"
        ).status_code
        == 400
    )
    for data in [
        {"employee_id": t.colleague.pk},
        {"task_id": t.task.pk},
        {"work_date": str(t.today + timedelta(days=1))},
    ]:
        assert (
            employee.patch(f"/api/time-entries/{entry.pk}/", data, format="json").status_code == 400
        )
    assert (
        employee.patch(
            f"/api/time-entries/{entry.pk}/", {"note": "Updated"}, format="json"
        ).status_code
        == 200
    )


def test_completed_locks_and_admin_corrections(world):
    t = world
    entry = time_entry(t)
    services.update_task(t.employee, t.task.pk, status=Task.Status.COMPLETED)
    for user in [t.manager, t.employee]:
        client = api(user)
        assert (
            client.patch(
                f"/api/tasks/{t.task.pk}/", {"status": "IN_PROGRESS"}, format="json"
            ).status_code
            == 403
        )
        assert client.delete(f"/api/tasks/{t.task.pk}/").status_code == 403
        assert (
            client.patch(
                f"/api/time-entries/{entry.pk}/", {"minutes": 2}, format="json"
            ).status_code
            == 403
        )
        assert client.delete(f"/api/time-entries/{entry.pk}/").status_code == 403
        assert (
            client.patch(
                f"/api/time-entries/{entry.pk}/correction/", {"minutes": 2}, format="json"
            ).status_code
            == 403
        )
        assert (
            client.patch(
                f"/api/tasks/{t.task.pk}/correction/", {"title": "Bad"}, format="json"
            ).status_code
            == 403
        )
    admin = api(t.admin)
    assert (
        admin.patch(
            f"/api/tasks/{t.task.pk}/correction/", {"title": "Corrected"}, format="json"
        ).status_code
        == 200
    )
    assert (
        admin.patch(
            f"/api/time-entries/{entry.pk}/correction/", {"minutes": 75}, format="json"
        ).status_code
        == 200
    )
    assert (
        admin.patch(
            f"/api/tasks/{t.task.pk}/correction/", {"status": "TODO"}, format="json"
        ).status_code
        == 400
    )
    entry.refresh_from_db()
    assert entry.task.status == "COMPLETED" and entry.employee_id == t.employee.pk


def test_accounts_admin_role_without_superuser(world):
    t = world
    assert not t.admin.is_superuser and not t.admin.is_staff
    client = api(t.admin)
    response = client.post(
        "/api/accounts/",
        {"username": "new", "password": "New-Initial!937", "role": "EMPLOYEE"},
        format="json",
    )
    assert response.status_code == 201
    user_id = response.json()["id"]
    assert set(response.json()) == {
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
    }
    created = User.objects.get(pk=user_id)
    assert created.check_password("New-Initial!937") and created.must_change_password
    assert (
        client.patch(f"/api/accounts/{user_id}/", {"first_name": "New"}, format="json").status_code
        == 200
    )
    assert client.get(f"/api/accounts/{user_id}/").status_code == 200
    assert client.post(f"/api/accounts/{user_id}/deactivate/", {}, format="json").status_code == 200
    created.refresh_from_db()
    assert not created.is_active
    for user in [t.manager, t.employee]:
        other = api(user)
        assert other.get("/api/accounts/").status_code == 403
        assert other.get(f"/api/accounts/{t.admin.pk}/").status_code == 403
        assert (
            other.post(
                "/api/accounts/",
                {"username": "bad", "password": "Strong-Secret!239"},
                format="json",
            ).status_code
            == 403
        )
        assert (
            other.patch(
                f"/api/accounts/{t.admin.pk}/", {"role": "EMPLOYEE"}, format="json"
            ).status_code
            == 403
        )
    assert client.delete(f"/api/accounts/{t.employee.pk}/").status_code == 405


@pytest.mark.parametrize(
    "field",
    ["is_staff", "is_superuser", "must_change_password", "groups", "user_permissions", "id"],
)
def test_account_protected_fields_400(world, field):
    client = api(world.admin)
    assert (
        client.patch(
            f"/api/accounts/{world.employee.pk}/", {field: True}, format="json"
        ).status_code
        == 400
    )


def test_account_role_guard_password_and_duplicate_validation(world):
    t = world
    client = api(t.admin)
    assert (
        client.patch(
            f"/api/accounts/{t.manager.pk}/", {"role": "EMPLOYEE"}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/accounts/{t.employee.pk}/", {"role": "ADMIN"}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/accounts/{t.employee.pk}/", {"password": "123"}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/accounts/",
            {"username": t.employee.username, "password": "Strong-Initial!291"},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post("/api/accounts/", {"username": "no-password"}, format="json").status_code == 400
    )


def test_employee_picker_minimal_active_and_owned(world):
    t = world
    inactive = User.objects.create_user("inactive", is_active=False, must_change_password=False)
    for user in [t.admin, t.manager]:
        response = api(user).get(f"/api/projects/{t.project.pk}/employee-options/")
        assert response.status_code == 200
        options = response.json()["results"]
        assert all(set(row) == {"id", "name"} for row in options)
        assert inactive.pk not in [row["id"] for row in options]
        assert t.manager.pk not in [row["id"] for row in options]
        assert t.outsider.pk in [row["id"] for row in options]
    assert api(t.employee).get(f"/api/projects/{t.project.pk}/employee-options/").status_code == 403


def test_csrf_real_mutation_and_login(world):
    t = world
    t.manager.set_password(TEST_PASSWORD)
    t.manager.save(update_fields=["password"])
    client = APIClient(enforce_csrf_checks=True)
    client.get("/login/")
    token = client.cookies["csrftoken"].value
    assert (
        client.post(
            "/login/",
            {
                "username": t.manager.username,
                "password": TEST_PASSWORD,
                "csrfmiddlewaretoken": token,
            },
        ).status_code
        == 302
    )
    token = client.cookies["csrftoken"].value
    url = f"/api/projects/{t.project.pk}/"
    assert client.patch(url, {"name": "CSRF"}, format="json").status_code == 403
    assert (
        client.patch(url, {"name": "CSRF"}, format="json", HTTP_X_CSRFTOKEN=token).status_code
        == 200
    )


@pytest.mark.parametrize("state", ["anonymous", "initial", "inactive"])
def test_all_new_apis_require_usable_session(world, state):
    client = APIClient()
    if state != "anonymous":
        user = world.admin
        client.force_login(user)
        setattr(
            user, "must_change_password" if state == "initial" else "is_active", state == "initial"
        )
        user.save()
    for url in [
        "/api/accounts/",
        "/api/projects/",
        "/api/tasks/",
        "/api/time-entries/",
        "/api/overview/",
    ]:
        assert client.get(url).status_code == 403


def test_safe_deletion_and_time_delete(world):
    t = world
    manager = api(t.manager)
    assert manager.delete(f"/api/projects/{t.project.pk}/").status_code == 400
    entry = time_entry(t)
    assert manager.delete(f"/api/tasks/{t.task.pk}/").status_code == 400
    assert api(t.employee).delete(f"/api/time-entries/{entry.pk}/").status_code == 204
    assert manager.delete(f"/api/tasks/{t.task.pk}/").status_code == 204
    assert (
        manager.delete(f"/api/projects/{t.project.pk}/memberships/{t.employee.pk}/").status_code
        == 204
    )
    assert (
        manager.delete(f"/api/projects/{t.project.pk}/memberships/{t.colleague.pk}/").status_code
        == 204
    )
    assert manager.delete(f"/api/projects/{t.project.pk}/").status_code == 204


@pytest.mark.parametrize("resource", ["projects", "tasks", "time-entries"])
def test_missing_detail_404(world, resource):
    response = api(world.admin).get(f"/api/{resource}/999999/")
    assert response.status_code == 404 and response.json() == {"detail": "Resource unavailable."}


def test_paginated_lists_have_stable_order(world):
    t = world
    for i in range(30):
        services.create_task(t.manager, t.project.pk, title=str(i), assignee_id=t.employee.pk)
    client = api(t.manager)
    first, second = client.get("/api/tasks/").json(), client.get("/api/tasks/?page=2").json()
    assert first["count"] == 31 and len(first["results"]) == 25 and len(second["results"]) == 6
    ids = [row["id"] for row in first["results"] + second["results"]]
    assert ids == sorted(set(ids))


def test_reports_multiple_entries_empty_and_historical_contributors(world):
    t = world
    time_entry(t, minutes=31)
    time_entry(t, minutes=29)
    second = services.create_task(
        t.manager, t.project.pk, title="Other", assignee_id=t.colleague.pk
    )
    time_entry(t, t.colleague, second, minutes=120)
    services.update_task(t.manager, t.task.pk, assignee_id=t.colleague.pk)
    services.remove_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    from accounts.services import deactivate_account

    deactivate_account(t.admin, t.employee.pk)
    manager = api(t.manager)
    report = manager.get(f"/api/projects/{t.project.pk}/report/").json()
    assert (
        report["total_tasks"] == 2 and report["total_minutes"] == 180 and report["total_hours"] == 3
    )
    assert {row["employee_id"]: row["minutes"] for row in report["contributors"]} == {
        t.employee.pk: 60,
        t.colleague.pk: 120,
    }
    services.update_task(t.manager, second.pk, status="COMPLETED")
    report = manager.get(f"/api/projects/{t.project.pk}/report/").json()
    assert report["completed_tasks"] == 1 and report["completion_percentage"] == 50
    empty = services.create_project(t.manager, name="Empty", start_date=t.today, end_date=t.today)
    report = manager.get(f"/api/projects/{empty.pk}/report/").json()
    assert report["total_tasks"] == report["completion_percentage"] == report["total_minutes"] == 0
    assert report["contributors"] == []
    assert manager.get("/api/overview/").json()["total_tasks"] == 2


@pytest.mark.django_db(transaction=True)
def test_sql_reports_match_multiple_entries_and_history(world):
    from scripts.verify_project_reports import verify

    t = world
    time_entry(t, minutes=31)
    time_entry(t, minutes=29)
    services.update_task(t.manager, t.task.pk, assignee_id=t.colleague.pk)
    services.remove_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    services.create_project(t.manager, name="Zero", start_date=t.today, end_date=t.today)
    result = verify()
    assert result["result"] == "MATCH" and result["projects_compared"] == 3
    assert result["contributors_compared"] == 1


@pytest.mark.django_db(transaction=True)
def test_sql_reports_match_seeded_data(settings):
    from io import StringIO

    from django.core.management import call_command

    from scripts.verify_project_reports import verify

    settings.DEBUG = True
    settings.DEMO_PASSWORD = TEST_PASSWORD
    call_command("seed_demo", stdout=StringIO())
    result = verify()
    assert result["result"] == "MATCH" and result["projects_compared"] == 4
    assert sorted(row["minutes"] for row in result["totals"]) == [0, 0, 720, 720]


def test_payload_formats_unknown_delete_and_missing_account(world):
    t = world
    client = api(t.manager)
    assert client.patch(f"/api/projects/{t.project.pk}/", {"name": "Form"}).status_code == 415
    assert (
        client.patch(
            f"/api/projects/{t.project.pk}/", data="{bad", content_type="application/json"
        ).status_code
        == 400
    )
    assert (
        client.delete(
            f"/api/projects/{t.project.pk}/", {"manager_id": t.foreign.pk}, format="json"
        ).status_code
        == 400
    )
    response = api(t.admin).get("/api/accounts/999999/")
    assert response.status_code == 404 and response.json() == {"detail": "Resource unavailable."}


def test_employee_overview_only_own_work_and_status_permissions(world):
    t = world
    time_entry(t, minutes=12)
    colleague_task = services.create_task(
        t.manager, t.project.pk, title="Colleague", assignee_id=t.colleague.pk
    )
    time_entry(t, t.colleague, colleague_task, minutes=180)
    client = api(t.employee)
    summary = client.get("/api/overview/").json()
    assert summary["scope"] == "own_work" and summary["total_tasks"] == 1
    assert summary["total_minutes"] == 12
    assert (
        client.patch(
            f"/api/tasks/{colleague_task.pk}/", {"status": "COMPLETED"}, format="json"
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/projects/{t.project.pk}/memberships/",
            {"employee_id": t.outsider.pk},
            format="json",
        ).status_code
        == 403
    )


def test_admin_ownership_update_and_deactivation_revokes_session(world):
    t = world
    client = api(t.admin)
    manager = api(t.manager)
    assert (
        client.patch(
            f"/api/projects/{t.project.pk}/", {"manager_id": t.foreign.pk}, format="json"
        ).status_code
        == 200
    )
    assert manager.get(f"/api/projects/{t.project.pk}/report/").status_code == 404
    assert (
        client.post(f"/api/accounts/{t.manager.pk}/deactivate/", {}, format="json").status_code
        == 200
    )
    assert manager.get("/api/projects/").status_code == 403
    assert Project.objects.get(pk=t.project.pk).manager_id == t.foreign.pk

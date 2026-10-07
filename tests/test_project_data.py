import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Event
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.models import Sum
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from accounts.models import User
from projects.models import Project, ProjectMembership, Task, TimeEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def data():
    manager = User.objects.create_user("manager", role=User.Role.PROJECT_MANAGER)
    other_manager = User.objects.create_user("other-manager", role=User.Role.PROJECT_MANAGER)
    employee = User.objects.create_user("employee")
    other_employee = User.objects.create_user("other-employee")
    inactive = User.objects.create_user("inactive", is_active=False)
    unassigned = User.objects.create_user("unassigned")
    admin = User.objects.create_superuser("admin")
    project = Project.objects.create(
        name="Website", manager=manager, start_date=date(2026, 10, 6), end_date=date(2026, 10, 23)
    )
    other_project = Project.objects.create(
        name="Other project",
        manager=other_manager,
        start_date=date(2026, 10, 6),
        end_date=date(2026, 10, 23),
    )
    membership = ProjectMembership.objects.create(project=project, employee=employee)
    ProjectMembership.objects.create(project=project, employee=other_employee)
    task = Task.objects.create(project=project, title="Design homepage", assignee=employee)
    return SimpleNamespace(
        manager=manager,
        other_manager=other_manager,
        employee=employee,
        other_employee=other_employee,
        inactive=inactive,
        unassigned=unassigned,
        admin=admin,
        project=project,
        other_project=other_project,
        membership=membership,
        task=task,
    )


def start(task):
    task.status = Task.Status.IN_PROGRESS
    task.save(update_fields=["status"])


def entry(data, **changes):
    values = dict(
        task=data.task, employee=data.employee, work_date=timezone.localdate(), minutes=60
    )
    values.update(changes)
    return TimeEntry.objects.create(**values)


def test_backend_and_relationships(data):
    assert connection.vendor == "postgresql"
    assert list(data.manager.managed_projects.all()) == [data.project]
    assert data.project.tasks.get() == data.task
    assert data.employee.assigned_tasks.get() == data.task
    assert data.employee.project_memberships.get() == data.membership
    assert data.task.status == Task.Status.TODO


def test_equal_project_dates_allowed(data):
    data.project.end_date = data.project.start_date
    data.project.save()


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("name", " \t\n"),
        ("name", "x" * 201),
        ("start_date", None),
        ("end_date", None),
        ("start_date", "not-a-date"),
        ("end_date", date(2026, 10, 5)),
    ],
)
def test_project_save_rejects_invalid_fields(data, field, value):
    setattr(data.project, field, value)
    with pytest.raises(ValidationError):
        data.project.save()
    assert Project.objects.get(pk=data.project.pk).name == "Website"


@pytest.mark.parametrize("role", [User.Role.ADMIN, User.Role.EMPLOYEE])
def test_manager_must_have_manager_role(data, role):
    person = data.admin if role == User.Role.ADMIN else data.employee
    data.project.manager = person
    with pytest.raises(ValidationError, match="Project Manager"):
        data.project.save(update_fields=["manager"])


def test_inactive_manager_cannot_receive_new_project(data):
    data.other_manager.is_active = False
    data.other_manager.save(update_fields=["is_active"])
    data.project.manager = data.other_manager
    with pytest.raises(ValidationError):
        data.project.save()
    # Historical ownership remains valid after deactivation.
    data.manager.is_active = False
    data.manager.save(update_fields=["is_active"])
    data.project.refresh_from_db()
    data.project.description = "Ownership retained"
    data.project.save()


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("name", " \t\n"),
        ("end_date", date(2026, 10, 5)),
        ("start_date", None),
        ("manager_id", None),
    ],
)
def test_project_database_constraints_when_validation_is_bypassed(data, field, value):
    with pytest.raises(IntegrityError), transaction.atomic():
        Project.objects.filter(pk=data.project.pk).update(**{field: value})


def test_partial_project_save_validates_persisted_end_date(data):
    data.project.start_date = date(2026, 10, 24)
    data.project.end_date = date(2026, 10, 30)  # Not included in this write.
    with pytest.raises(ValidationError, match="End date"):
        data.project.save(update_fields=["start_date"])
    data.project.refresh_from_db()
    assert data.project.start_date == date(2026, 10, 6)


@pytest.mark.parametrize("person", ["manager", "admin", "inactive"])
def test_membership_requires_active_employee(data, person):
    with pytest.raises(ValidationError, match="active Employee"):
        ProjectMembership.objects.create(project=data.project, employee=getattr(data, person))


def test_duplicate_membership_validation_and_database_constraint(data):
    with pytest.raises(ValidationError):
        ProjectMembership.objects.create(project=data.project, employee=data.employee)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectMembership.objects.bulk_create(
            [
                ProjectMembership(project=data.project, employee=data.employee),
            ]
        )


def test_membership_identity_cannot_change(data):
    data.membership.project = data.other_project
    with pytest.raises(ValidationError):
        data.membership.save(update_fields=["project"])


@pytest.mark.parametrize("person", ["unassigned", "manager", "admin", "inactive"])
def test_task_new_assignee_requires_active_project_member(data, person):
    with pytest.raises(ValidationError):
        Task.objects.create(project=data.project, title="New task", assignee=getattr(data, person))


def test_inactive_member_cannot_receive_new_assignment(data):
    data.other_employee.is_active = False
    data.other_employee.save(update_fields=["is_active"])
    data.task.assignee = data.other_employee
    with pytest.raises(ValidationError, match="active Employee"):
        data.task.save(update_fields=["assignee"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", ""),
        ("title", " \n"),
        ("title", "x" * 201),
        ("status", "BLOCKED"),
        ("assignee_id", None),
        ("project_id", None),
    ],
)
def test_task_save_validates_required_fields_and_status(data, field, value):
    setattr(data.task, field, value)
    with pytest.raises(ValidationError):
        data.task.save()


@pytest.mark.parametrize("status", [Task.Status.IN_PROGRESS, Task.Status.COMPLETED])
def test_new_task_must_begin_todo(data, status):
    with pytest.raises(ValidationError, match="New tasks"):
        Task.objects.create(
            project=data.project, assignee=data.employee, title="New", status=status
        )


def test_forward_transitions_and_same_status_noop(data):
    data.task.save(update_fields=["status"])
    data.task.status = Task.Status.COMPLETED
    with pytest.raises(ValidationError, match="one step"):
        data.task.save()
    start(data.task)
    data.task.status = Task.Status.TODO
    with pytest.raises(ValidationError):
        data.task.save()
    data.task.status = Task.Status.COMPLETED
    data.task.save()
    data.task.save(update_fields=["status"])
    data.task.status = Task.Status.IN_PROGRESS
    with pytest.raises(ValidationError, match="cannot reopen"):
        data.task.save()


def test_task_cannot_move_project(data):
    data.task.project = data.other_project
    with pytest.raises(ValidationError, match="cannot move"):
        data.task.save()


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "BLOCKED"),
        ("title", " \n"),
        ("assignee_id", None),
        ("project_id", None),
    ],
)
def test_task_row_constraints_when_validation_is_bypassed(data, field, value):
    with pytest.raises(IntegrityError), transaction.atomic():
        Task.objects.filter(pk=data.task.pk).update(**{field: value})


def test_partial_task_update_uses_fresh_assignee(data):
    stale = Task.objects.get(pk=data.task.pk)
    data.task.assignee = data.other_employee
    data.task.save(update_fields=["assignee"])
    stale.status = Task.Status.IN_PROGRESS
    stale.save(update_fields=["status"])
    assert Task.objects.get(pk=stale.pk).assignee == data.other_employee


@pytest.mark.parametrize("minutes", [0, -1, 1441, True, False, 1.5, 1.0, "60", Decimal("60"), None])
def test_minutes_validation_rejects_invalid_or_coercible_values(data, minutes):
    start(data.task)
    with pytest.raises(ValidationError):
        entry(data, minutes=minutes)
    assert not TimeEntry.objects.exists()


@pytest.mark.parametrize("minutes", [1, 1440])
def test_whole_minutes_boundaries_allowed(data, minutes):
    start(data.task)
    assert entry(data, minutes=minutes).minutes == minutes


@pytest.mark.parametrize("minutes", [0, -1, 1441])
def test_minutes_database_bounds(data, minutes):
    start(data.task)
    record = entry(data)
    with pytest.raises(IntegrityError), transaction.atomic():
        TimeEntry.objects.filter(pk=record.pk).update(minutes=minutes)


@pytest.mark.parametrize("work_date", [None, "not-a-date"])
def test_invalid_work_dates_are_validation_errors(data, work_date):
    start(data.task)
    with pytest.raises(ValidationError):
        entry(data, work_date=work_date)


def test_future_work_date_rejected_on_create_and_update(data):
    start(data.task)
    future = timezone.localdate() + timedelta(days=1)
    with pytest.raises(ValidationError, match="future"):
        entry(data, work_date=future)
    record = entry(data)
    record.work_date = future
    with pytest.raises(ValidationError):
        record.save(update_fields=["work_date"])


def test_time_only_for_own_active_assigned_in_progress_task(data):
    with pytest.raises(ValidationError, match="In progress"):
        entry(data)
    start(data.task)
    with pytest.raises(ValidationError, match="assigned employee"):
        entry(data, employee=data.other_employee)
    data.employee.is_active = False
    data.employee.save(update_fields=["is_active"])
    with pytest.raises(ValidationError, match="active Employee"):
        entry(data)
    data.task.status = Task.Status.COMPLETED
    data.task.save()
    with pytest.raises(ValidationError, match="In progress"):
        entry(data)


def test_time_requires_membership_even_if_task_assignment_was_bypassed(data):
    start(data.task)
    Task.objects.filter(pk=data.task.pk).update(assignee=data.unassigned)
    with pytest.raises(ValidationError, match="belong"):
        entry(data, employee=data.unassigned)


def test_historical_attribution_survives_reassignment_membership_removal_and_deactivation(data):
    start(data.task)
    original = entry(data)
    data.task.assignee = data.other_employee
    data.task.save(update_fields=["assignee"])
    data.membership.delete()
    data.employee.is_active = False
    data.employee.save(update_fields=["is_active"])
    entry(data, employee=data.other_employee, minutes=120)
    original.refresh_from_db()
    assert original.employee == data.employee
    assert original.task == data.task
    assert (
        TimeEntry.objects.filter(employee=data.employee).aggregate(total=Sum("minutes"))["total"]
        == 60
    )
    assert (
        TimeEntry.objects.filter(employee=data.other_employee).aggregate(total=Sum("minutes"))[
            "total"
        ]
        == 120
    )
    original.full_clean()  # Historical data no longer requires current membership/activity.


def test_original_time_task_and_employee_are_immutable(data):
    start(data.task)
    record = entry(data)
    record.employee = data.other_employee
    with pytest.raises(ValidationError, match="original"):
        record.save(update_fields=["employee"])
    record.refresh_from_db()
    other = Task.objects.create(project=data.project, assignee=data.employee, title="Other")
    start(other)
    record.task = other
    with pytest.raises(ValidationError, match="original"):
        record.save(update_fields=["task"])


@pytest.mark.parametrize("queryset", [False, True])
def test_membership_removal_rejected_with_unfinished_tasks(data, queryset):
    with pytest.raises(ValidationError, match="unfinished"):
        if queryset:
            ProjectMembership.objects.filter(project=data.project).delete()
        else:
            data.membership.delete()
    assert ProjectMembership.objects.filter(pk=data.membership.pk).exists()


def test_completed_assignment_allows_membership_removal_without_history_loss(data):
    start(data.task)
    record = entry(data)
    data.task.status = Task.Status.COMPLETED
    data.task.save()
    data.membership.delete()
    data.task.full_clean()
    assert TimeEntry.objects.get(pk=record.pk).employee == data.employee
    assert Task.objects.get(pk=data.task.pk).assignee == data.employee


def test_dependent_projects_tasks_and_users_are_protected(data):
    start(data.task)
    record = entry(data)
    for obj in [data.project, data.task, data.employee, data.manager]:
        with pytest.raises(ProtectedError):
            obj.delete()
    with pytest.raises(ProtectedError):
        Task.objects.filter(pk=data.task.pk).delete()
    assert TimeEntry.objects.get(pk=record.pk).minutes == 60


def test_empty_project_and_task_without_time_can_be_deleted(data):
    data.other_project.delete()
    data.task.delete()
    data.membership.delete()
    assert not TimeEntry.objects.exists()


def test_foreign_keys_protect_against_missing_references(data):
    with pytest.raises(IntegrityError), transaction.atomic():
        Task.objects.filter(pk=data.task.pk).update(assignee_id=999999)
        connection.check_constraints()


def test_time_partial_update_validates_the_effective_minutes(data):
    start(data.task)
    record = entry(data)
    record.minutes = 1.5
    with pytest.raises(ValidationError, match="whole minutes"):
        record.save(update_fields=["minutes"])
    # Unsaved bad minutes must not obstruct a note-only update.
    record.note = "Reviewed note"
    record.save(update_fields=["note"])
    record.refresh_from_db()
    assert record.minutes == 60 and record.note == "Reviewed note"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("first_action", ["assign", "remove"])
def test_assignment_and_membership_removal_serialize_on_postgresql(data, first_action):
    data.task.delete()
    held, release, attempting = Event(), Event(), Event()
    state = {}

    def mutate(action, first):
        close_old_connections()
        try:
            connection.ensure_connection()
            if not first:
                state["pid"] = connection.connection.info.backend_pid
                attempting.set()
            with transaction.atomic():
                if action == "assign":
                    Task.objects.create(
                        project_id=data.project.pk, assignee_id=data.employee.pk, title="Concurrent"
                    )
                else:
                    ProjectMembership.objects.get(pk=data.membership.pk).delete()
                if first:
                    held.set()
                    assert release.wait(5), "Timed out waiting to release project lock"
            return "saved"
        except ValidationError:
            return "rejected"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        winner = pool.submit(mutate, first_action, True)
        try:
            assert held.wait(5), "First mutation failed to acquire/hold the project lock"
            loser = pool.submit(mutate, "remove" if first_action == "assign" else "assign", False)
            assert attempting.wait(5)
            deadline = time.monotonic() + 5
            blocked = False
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s",
                        [state["pid"]],
                    )
                    row = cursor.fetchone()
                if row and row[0] == "Lock":
                    blocked = True
                    break
                time.sleep(0.01)
            assert blocked, "Second mutation did not wait on the PostgreSQL project lock"
        finally:
            release.set()
        assert winner.result(timeout=5) == "saved"
        assert loser.result(timeout=5) == "rejected"
    has_membership = ProjectMembership.objects.filter(pk=data.membership.pk).exists()
    has_task = Task.objects.filter(project=data.project, title="Concurrent").exists()
    assert has_membership == has_task == (first_action == "assign")

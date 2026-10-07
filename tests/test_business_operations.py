from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import connection
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from accounts import services as accounts
from accounts.models import User
from projects import selectors
from projects import services as ops
from projects.models import Project, ProjectMembership, Task, TimeEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def team():
    users = {}
    for name, role in [
        ("admin", User.Role.ADMIN),
        ("manager", User.Role.PROJECT_MANAGER),
        ("foreign", User.Role.PROJECT_MANAGER),
        ("employee", User.Role.EMPLOYEE),
        ("colleague", User.Role.EMPLOYEE),
        ("outsider", User.Role.EMPLOYEE),
    ]:
        users[name] = User.objects.create_user(username=name, role=role, must_change_password=False)
    t = SimpleNamespace(**users)
    t.today = timezone.localdate()
    t.project = ops.create_project(t.manager, name="Delivery", start_date=t.today, end_date=t.today)
    t.other = ops.create_project(t.foreign, name="Other", start_date=t.today, end_date=t.today)
    for user in [t.employee, t.colleague]:
        ops.add_member(t.manager, t.project.pk, employee_id=user.pk)
    t.task = ops.create_task(t.manager, t.project.pk, title="Build", assignee_id=t.employee.pk)
    return t


def start_time(t):
    ops.update_task(t.employee, t.task.pk, status=Task.Status.IN_PROGRESS)
    return ops.create_time_entry(
        t.employee, t.task.pk, minutes=60, work_date=t.today, note="Private"
    )


def test_complete_journey(team):
    t = team
    assert connection.vendor == "postgresql"
    entry = start_time(t)
    ops.update_time_entry(t.employee, entry.pk, minutes=90)
    spare = ops.create_time_entry(t.employee, t.task.pk, minutes=1, work_date=t.today)
    ops.delete_time_entry(t.employee, spare.pk)
    ops.update_task(t.employee, t.task.pk, status=Task.Status.COMPLETED)
    ops.update_task(t.employee, t.task.pk, status=Task.Status.COMPLETED)
    ops.remove_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    entry.refresh_from_db()
    assert entry.minutes == 90 and entry.employee_id == t.employee.pk
    assert entry.task.status == Task.Status.COMPLETED


@pytest.mark.parametrize("who", ["foreign", "outsider"])
@pytest.mark.parametrize("action", ["project", "member", "task", "time", "delete"])
def test_foreign_records_denied(team, who, action):
    t = team
    entry = start_time(t)
    actor = getattr(t, who)
    actions = {
        "project": lambda: ops.update_project(actor, t.project.pk, name="Stolen"),
        "member": lambda: ops.add_member(actor, t.project.pk, employee_id=t.outsider.pk),
        "task": lambda: ops.update_task(actor, t.task.pk, status=Task.Status.COMPLETED),
        "time": lambda: ops.update_time_entry(actor, entry.pk, note="Stolen"),
        "delete": lambda: ops.delete_task(actor, t.task.pk),
    }
    with pytest.raises((ObjectDoesNotExist, PermissionDenied)):
        actions[action]()


def test_colleague_cannot_edit_task_or_time(team):
    t = team
    entry = start_time(t)
    for action in [
        lambda: ops.update_task(t.colleague, t.task.pk, status=Task.Status.COMPLETED),
        lambda: ops.create_time_entry(t.colleague, t.task.pk, minutes=1, work_date=t.today),
        lambda: ops.update_time_entry(t.colleague, entry.pk, minutes=1),
        lambda: ops.delete_time_entry(t.colleague, entry.pk),
    ]:
        with pytest.raises(PermissionDenied):
            action()


@pytest.mark.parametrize("field", ["manager_id", "manager", "demo_key", "id"])
def test_manager_cannot_forge_project_fields(team, field):
    with pytest.raises(ValidationError):
        ops.update_project(team.manager, team.project.pk, **{field: team.foreign.pk})
    with pytest.raises(ValidationError):
        ops.create_project(
            team.manager,
            name="Bad",
            start_date=team.today,
            end_date=team.today,
            **{field: team.foreign.pk},
        )


def test_admin_ownership_and_validation(team):
    t = team
    ops.update_project(t.admin, t.project.pk, manager_id=t.foreign.pk)
    with pytest.raises(ObjectDoesNotExist):
        ops.update_project(t.manager, t.project.pk, name="Old owner")
    with pytest.raises(ValidationError):
        ops.update_project(t.admin, t.project.pk, manager_id=t.employee.pk)
    with pytest.raises(ValidationError):
        ops.update_project(t.foreign, t.project.pk, end_date=t.today - timedelta(days=1))
    p = ops.create_project(
        t.admin, manager_id=t.manager.pk, name="Empty", start_date=t.today, end_date=t.today
    )
    ops.delete_project(t.admin, p.pk)
    with pytest.raises(ProtectedError):
        ops.delete_project(t.admin, t.project.pk)


def test_membership_and_assignment_rules_reused(team):
    t = team
    with pytest.raises(ValidationError):
        ops.add_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    with pytest.raises(ValidationError):
        ops.remove_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    with pytest.raises(ValidationError):
        ops.update_task(t.manager, t.task.pk, assignee_id=t.outsider.pk)
    accounts.deactivate_account(t.admin, t.colleague.pk)
    with pytest.raises(ValidationError):
        ops.update_task(t.manager, t.task.pk, assignee_id=t.colleague.pk)
    with pytest.raises(ValidationError):
        ops.add_member(t.admin, t.other.pk, employee_id=t.colleague.pk)


@pytest.mark.parametrize("field", ["project_id", "project", "id"])
def test_task_project_and_protected_fields(team, field):
    with pytest.raises(ValidationError):
        ops.update_task(team.manager, team.task.pk, **{field: team.other.pk})


def test_employee_field_whitelist_and_forward_only(team):
    t = team
    with pytest.raises(ValidationError):
        ops.update_task(t.employee, t.task.pk, title="Forged")
    with pytest.raises(ValidationError):
        ops.update_task(t.employee, t.task.pk, status=Task.Status.COMPLETED)
    with pytest.raises(ValidationError):
        ops.create_task(
            t.manager,
            t.project.pk,
            title="Skipped",
            assignee_id=t.employee.pk,
            status=Task.Status.IN_PROGRESS,
        )
    ops.update_task(t.employee, t.task.pk, status=Task.Status.TODO)


@pytest.mark.parametrize("who", ["manager", "employee", "colleague"])
def test_completed_mutation_locks(team, who):
    t = team
    entry = start_time(t)
    ops.update_task(t.employee, t.task.pk, status=Task.Status.COMPLETED)
    actor = getattr(t, who)
    actions = [
        lambda: ops.update_task(actor, t.task.pk, title="Edited"),
        lambda: ops.update_task(actor, t.task.pk, assignee_id=t.colleague.pk),
        lambda: ops.delete_task(actor, t.task.pk),
        lambda: ops.update_time_entry(actor, entry.pk, minutes=2),
        lambda: ops.delete_time_entry(actor, entry.pk),
        lambda: ops.create_time_entry(actor, t.task.pk, minutes=1, work_date=t.today),
        lambda: ops.correct_completed_task(actor, t.task.pk, title="Edited"),
        lambda: ops.correct_time_entry(actor, entry.pk, minutes=1),
    ]
    for action in actions:
        with pytest.raises((PermissionDenied, ValidationError)):
            action()
    entry.refresh_from_db()
    assert entry.minutes == 60 and entry.task.title == "Build"


def test_explicit_admin_corrections_preserve_identity_and_status(team):
    t = team
    entry = start_time(t)
    ops.update_task(t.manager, t.task.pk, status=Task.Status.COMPLETED)
    ops.correct_completed_task(t.admin, t.task.pk, title="Corrected", assignee_id=t.colleague.pk)
    ops.correct_time_entry(t.admin, entry.pk, minutes=75, note="Corrected note")
    for data in [{"employee_id": t.colleague.pk}, {"task_id": t.task.pk}, {"id": 99}]:
        with pytest.raises(ValidationError):
            ops.correct_time_entry(t.admin, entry.pk, **data)
    with pytest.raises(ValidationError):
        ops.correct_completed_task(t.admin, t.task.pk, status=Task.Status.TODO)
    entry.refresh_from_db()
    assert (entry.employee_id, entry.task_id, entry.minutes) == (t.employee.pk, t.task.pk, 75)
    assert entry.task.status == Task.Status.COMPLETED


def test_reassignment_removes_old_contributor_write_access(team):
    t = team
    entry = start_time(t)
    ops.update_task(t.manager, t.task.pk, assignee_id=t.colleague.pk)
    for actor in [t.employee, t.colleague, t.manager, t.admin]:
        with pytest.raises(PermissionDenied):
            ops.update_time_entry(actor, entry.pk, note="Overwrite")
    ops.remove_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    accounts.deactivate_account(t.admin, t.employee.pk)
    entry.refresh_from_db()
    assert entry.employee_id == t.employee.pk and entry.note == "Private"


@pytest.mark.parametrize(
    "data",
    [
        {"minutes": 1.5},
        {"minutes": True},
        {"minutes": 0},
        {"minutes": 1441},
        {"employee_id": 999},
        {"task": 999},
    ],
)
def test_time_validation_and_forgery(team, data):
    entry = start_time(team)
    with pytest.raises(ValidationError):
        ops.update_time_entry(team.employee, entry.pk, **data)
    with pytest.raises(ValidationError):
        ops.create_time_entry(
            team.employee, team.task.pk, **({"minutes": 1, "work_date": team.today} | data)
        )


def test_future_time_rejected(team):
    entry = start_time(team)
    with pytest.raises(ValidationError):
        ops.update_time_entry(team.employee, entry.pk, work_date=team.today + timedelta(days=1))


def test_scoped_lists_details_and_private_notes(team):
    t = team
    entry = start_time(t)
    task2 = ops.create_task(t.manager, t.project.pk, title="Team", assignee_id=t.colleague.pk)
    ops.update_task(t.colleague, task2.pk, status=Task.Status.IN_PROGRESS)
    other_entry = ops.create_time_entry(
        t.colleague, task2.pk, minutes=1, work_date=t.today, note="Colleague secret"
    )
    assert set(selectors.projects_for(t.admin)) == {t.project, t.other}
    for actor in [t.manager, t.employee, t.colleague]:
        assert list(selectors.projects_for(actor)) == [t.project]
        with pytest.raises(Project.DoesNotExist):
            selectors.project_for(actor, t.other.pk)
    assert selectors.projects_for(t.outsider).count() == 0
    assert selectors.tasks_for(t.foreign).count() == 0
    assert selectors.time_entries_for(t.foreign).count() == 0
    assert list(selectors.time_entries_for(t.employee)) == [entry]
    assert selectors.time_entries_for(t.manager).count() == 2
    assert selectors.time_entries_for(t.admin).count() == 2
    assert len(list(selectors.task_summaries_for(t.employee))) == 2
    assert selectors.task_for(t.employee, task2.pk) == task2
    with pytest.raises(TimeEntry.DoesNotExist):
        selectors.time_entry_for(t.employee, other_entry.pk)
    with pytest.raises(Task.DoesNotExist):
        selectors.task_for(t.foreign, t.task.pk)


@pytest.mark.parametrize("who", ["manager", "employee", "foreign"])
def test_account_operations_admin_only(team, who):
    actor = getattr(team, who)
    for action in [
        lambda: accounts.create_account(actor, username="new", password="Good-Secret!826"),
        lambda: accounts.update_account(actor, team.employee.pk, role=User.Role.ADMIN),
        lambda: accounts.deactivate_account(actor, team.employee.pk),
    ]:
        with pytest.raises(PermissionDenied):
            action()


def test_account_password_and_protected_fields(team):
    t = team
    user = accounts.create_account(t.admin, username="new", password="New-Secret!826")
    assert user.check_password("New-Secret!826") and user.must_change_password
    assert not user.is_staff and not user.is_superuser
    for field in ["is_staff", "is_superuser", "groups", "user_permissions", "must_change_password"]:
        with pytest.raises(ValidationError):
            accounts.update_account(t.admin, user.pk, **{field: True})
        with pytest.raises(ValidationError):
            accounts.create_account(
                t.admin, username="bad", password="New-Secret!826", **{field: True}
            )
    for password in ["123", "", None]:
        with pytest.raises(ValidationError):
            accounts.update_account(t.admin, user.pk, password=password)
    user = accounts.update_account(t.admin, t.employee.pk, password="Reset-Secret!928")
    assert user.check_password("Reset-Secret!928") and user.must_change_password


def test_role_changes_require_reassignment_and_preserve_history(team):
    t = team
    entry = start_time(t)
    for user in [t.manager, t.employee, t.colleague]:
        with pytest.raises(ValidationError, match="Reassign|Remove"):
            accounts.update_account(t.admin, user.pk, role=User.Role.ADMIN)
    ops.update_task(t.manager, t.task.pk, status=Task.Status.COMPLETED)
    ops.remove_member(t.manager, t.project.pk, employee_id=t.employee.pk)
    accounts.update_account(t.admin, t.employee.pk, role=User.Role.PROJECT_MANAGER)
    entry.refresh_from_db()
    assert entry.employee_id == t.employee.pk
    ops.update_project(t.admin, t.project.pk, manager_id=t.foreign.pk)
    accounts.update_account(t.admin, t.manager.pk, role=User.Role.EMPLOYEE)


@pytest.mark.parametrize("state", ["anonymous", "inactive", "initial", "changed_role"])
def test_fresh_actor_checks(team, state):
    t = team
    actor = t.manager
    if state == "anonymous":
        actor = AnonymousUser()
    elif state == "inactive":
        accounts.deactivate_account(t.admin, actor.pk)
    elif state == "initial":
        accounts.update_account(t.admin, actor.pk, password="Reset-Secret!928")
    else:
        ops.update_project(t.admin, t.project.pk, manager_id=t.foreign.pk)
        accounts.update_account(t.admin, actor.pk, role=User.Role.EMPLOYEE)
    with pytest.raises((PermissionDenied, ObjectDoesNotExist)):
        ops.update_project(actor, t.project.pk, name="Stale")
    if state != "changed_role":
        with pytest.raises(PermissionDenied):
            selectors.projects_for(actor)


@pytest.mark.parametrize("action", ["create_project", "create_task", "add", "remove", "delete"])
def test_member_cannot_manage_project(team, action):
    t = team
    actions = {
        "create_project": lambda: ops.create_project(
            t.employee, name="Bad", start_date=t.today, end_date=t.today
        ),
        "create_task": lambda: ops.create_task(
            t.employee, t.project.pk, title="Bad", assignee_id=t.employee.pk
        ),
        "add": lambda: ops.add_member(t.employee, t.project.pk, employee_id=t.outsider.pk),
        "remove": lambda: ops.remove_member(t.employee, t.project.pk, employee_id=t.colleague.pk),
        "delete": lambda: ops.delete_project(t.employee, t.project.pk),
    }
    with pytest.raises(PermissionDenied):
        actions[action]()


def test_django_admin_cannot_bypass_existing_role_guard(team):
    from django.contrib.admin.sites import AdminSite

    from accounts.admin import AccountAdmin

    admin = AccountAdmin(User, AdminSite())
    assert "role" in admin.get_readonly_fields(SimpleNamespace(user=team.admin), team.manager)


@pytest.mark.django_db(transaction=True)
def test_deactivation_serializes_with_new_membership(team):
    # Concrete race: a member must not be added after a concurrent deactivation commits.
    import time
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from django.db import close_old_connections, transaction

    held, release, attempting = Event(), Event(), Event()
    state = {}

    def deactivate():
        close_old_connections()
        try:
            with transaction.atomic():
                accounts.deactivate_account(team.admin, team.outsider.pk)
                held.set()
                assert release.wait(5)
        finally:
            connection.close()

    def add():
        close_old_connections()
        try:
            connection.ensure_connection()
            state["pid"] = connection.connection.info.backend_pid
            attempting.set()
            ops.add_member(team.manager, team.project.pk, employee_id=team.outsider.pk)
            return "added"
        except ValidationError:
            return "rejected"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(deactivate)
        try:
            assert held.wait(5)
            second = pool.submit(add)
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
            assert blocked
        finally:
            release.set()
        first.result(timeout=5)
        assert second.result(timeout=5) == "rejected"
    assert not ProjectMembership.objects.filter(employee=team.outsider).exists()

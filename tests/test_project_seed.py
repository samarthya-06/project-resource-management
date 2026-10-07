from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum

from accounts.models import User
from projects.models import Project, ProjectMembership, Task, TimeEntry
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def seed(settings):
    settings.DEBUG = True
    settings.DEMO_PASSWORD = TEST_PASSWORD

    def run():
        output = StringIO()
        call_command("seed_demo", stdout=output)
        return output.getvalue()

    return run


def test_seed_matches_paper_totals_and_role_scenarios(seed):
    seed()
    neha = User.objects.get(username="neha@demo.local")
    arjun = User.objects.get(username="arjun@demo.local")
    assert neha.role == arjun.role == User.Role.PROJECT_MANAGER
    assert neha.managed_projects.count() == 3
    assert arjun.managed_projects.count() == 1
    website = Project.objects.get(demo_key="website-redesign")
    assert website.name == "Client Website Redesign"
    assert website.start_date.isoformat() == "2026-10-06"
    assert website.end_date.isoformat() == "2026-10-23"
    assert website.tasks.count() == 6
    assert website.tasks.filter(status=Task.Status.COMPLETED).count() == 2
    assert (
        TimeEntry.objects.filter(task__project=website).aggregate(total=Sum("minutes"))["total"]
        == 720
    )
    contributors = dict(
        TimeEntry.objects.filter(task__project=website)
        .values("employee__username")
        .annotate(total=Sum("minutes"))
        .values_list("employee__username", "total")
    )
    assert contributors == {"asha@demo.local": 420, "ravi@demo.local": 300}
    expected = {
        "Design homepage layout": ("IN_PROGRESS", "asha@demo.local", 180),
        "Implement navigation": ("IN_PROGRESS", "ravi@demo.local", 120),
        "Review page content": ("TODO", "asha@demo.local", 0),
        "Test mobile navigation": ("TODO", "ravi@demo.local", 0),
        "Audit existing website": ("COMPLETED", "asha@demo.local", 240),
        "Define content structure": ("COMPLETED", "ravi@demo.local", 180),
    }
    assert {
        task.title: (
            task.status,
            task.assignee.username,
            task.time_entries.aggregate(total=Sum("minutes"))["total"] or 0,
        )
        for task in website.tasks.select_related("assignee")
    } == expected
    onboarding = Project.objects.get(demo_key="onboarding-portal")
    assert onboarding.tasks.count() == 5
    assert onboarding.tasks.filter(status=Task.Status.COMPLETED).count() == 2
    assert (
        TimeEntry.objects.filter(task__project=onboarding).aggregate(total=Sum("minutes"))["total"]
        == 720
    )
    empty = Project.objects.get(demo_key="knowledge-base")
    assert empty.tasks.count() == empty.memberships.count() == 0
    own_tasks = Task.objects.filter(project__manager=neha)
    assert own_tasks.exclude(status=Task.Status.COMPLETED).count() == 7
    assert own_tasks.filter(status=Task.Status.COMPLETED).count() == 4
    assert (
        TimeEntry.objects.filter(task__project__manager=neha).aggregate(total=Sum("minutes"))[
            "total"
        ]
        == 1440
    )
    asha = User.objects.get(username="asha@demo.local")
    assert {
        status: asha.assigned_tasks.filter(status=status).count() for status in Task.Status.values
    } == {
        "TODO": 2,
        "IN_PROGRESS": 2,
        "COMPLETED": 2,
    }
    assert asha.time_entries.aggregate(total=Sum("minutes"))["total"] == 780
    assert not User.objects.get(username="meera@demo.local").is_active
    assert not ProjectMembership.objects.filter(employee__username="meera@demo.local").exists()
    dev = User.objects.get(username="dev@demo.local")
    assert not dev.project_memberships.exists() and not dev.assigned_tasks.exists()


def snapshot():
    return {
        model.__name__: list(model.objects.order_by("pk").values())
        for model in [User, Project, ProjectMembership, Task, TimeEntry]
    }


def test_repeating_seed_preserves_every_record(seed):
    seed()
    before = snapshot()
    assert (
        User.objects.count(),
        Project.objects.count(),
        ProjectMembership.objects.count(),
        Task.objects.count(),
        TimeEntry.objects.count(),
    ) == (7, 4, 5, 12, 7)
    output = seed()
    assert snapshot() == before
    assert "Preserved demo project" in output
    assert TEST_PASSWORD not in output


def test_seed_preserves_edited_demo_data_and_does_not_restore_deleted_children(seed):
    seed()
    project = Project.objects.get(demo_key="website-redesign")
    project.name = "Renamed by user"
    project.description = "My work"
    project.save()
    task = project.tasks.get(title="Review page content")
    task.title = "Edited task title"
    task.save()
    record = TimeEntry.objects.get(task__title="Design homepage layout")
    record.minutes = 200
    record.note = "User's original note"
    record.save()
    project.tasks.get(title="Test mobile navigation").delete()
    asha = User.objects.get(username="asha@demo.local")
    asha.set_password("Changed-Secret!437")
    asha.first_name = "Edited name"
    asha.is_active = False
    asha.save()
    before = snapshot()
    seed()
    assert snapshot() == before


def test_seed_preserves_unrelated_work_even_with_same_display_names(seed):
    manager = User.objects.create_user("real-manager", role=User.Role.PROJECT_MANAGER)
    employee = User.objects.create_user("real-employee")
    project = Project.objects.create(
        name="Client Website Redesign",
        manager=manager,
        start_date="2026-10-06",
        end_date="2026-10-23",
    )
    ProjectMembership.objects.create(project=project, employee=employee)
    task = Task.objects.create(project=project, title="Review page content", assignee=employee)
    before = Project.objects.filter(pk=project.pk).values().get()
    seed()
    assert Project.objects.filter(pk=project.pk).values().get() == before
    assert Task.objects.get(pk=task.pk).status == Task.Status.TODO
    assert Project.objects.filter(name="Client Website Redesign").count() == 2


def test_seed_fails_atomically_instead_of_changing_conflicting_existing_account(seed):
    existing = User.objects.create_user("neha@demo.local", role=User.Role.EMPLOYEE)
    before = snapshot()
    with pytest.raises(CommandError, match="active Project Manager"):
        seed()
    assert snapshot() == before
    assert User.objects.get(pk=existing.pk).role == User.Role.EMPLOYEE


def test_demo_key_survives_rename_and_cannot_be_reassigned(seed):
    seed()
    project = Project.objects.get(demo_key="knowledge-base")
    project.demo_key = None
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="demo identity"):
        project.save(update_fields=["demo_key"])

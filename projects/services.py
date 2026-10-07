"""Authorized operations shared by future HTML and REST entry points."""

from django.core.exceptions import PermissionDenied
from django.db import transaction

from accounts.models import User
from accounts.services import check_fields, lock_actor
from projects.models import Project, ProjectMembership, Task, TimeEntry
from projects.selectors import projects_for


def _project(actor, project_id):
    return projects_for(actor).select_for_update().get(pk=project_id)


def _manage(actor, project):
    if actor.role != User.Role.ADMIN and not (
        actor.role == User.Role.PROJECT_MANAGER and project.manager_id == actor.pk
    ):
        raise PermissionDenied("Only Admin or the owning Manager can manage this project.")


def _task(actor, task_id):
    project_id = Task.objects.values_list("project_id", flat=True).get(pk=task_id)
    project = _project(actor, project_id)
    return Task.objects.get(pk=task_id, project=project)


def _save(instance, data):
    for field, value in data.items():
        setattr(instance, field, value)
    instance.save()
    return instance


@transaction.atomic
def create_project(actor, **data):
    actor = lock_actor(actor, data.get("manager_id"))
    if actor.role not in {User.Role.ADMIN, User.Role.PROJECT_MANAGER}:
        raise PermissionDenied("Only Admin or a Manager can create projects.")
    allowed = {"name", "description", "start_date", "end_date"}
    if actor.role == User.Role.ADMIN:
        allowed.add("manager_id")
    check_fields(data, allowed)
    if actor.role == User.Role.PROJECT_MANAGER:
        data["manager_id"] = actor.pk
    return Project.objects.create(**data)


@transaction.atomic
def update_project(actor, project_id, **data):
    actor = lock_actor(actor, data.get("manager_id"))
    project = _project(actor, project_id)
    _manage(actor, project)
    allowed = {"name", "description", "start_date", "end_date"}
    if actor.role == User.Role.ADMIN:
        allowed.add("manager_id")
    check_fields(data, allowed)
    return _save(project, data)


@transaction.atomic
def delete_project(actor, project_id):
    actor = lock_actor(actor)
    project = _project(actor, project_id)
    _manage(actor, project)
    return project.delete()


@transaction.atomic
def add_member(actor, project_id, *, employee_id, **data):
    actor = lock_actor(actor, employee_id)
    project = _project(actor, project_id)
    _manage(actor, project)
    check_fields(data, set())
    return ProjectMembership.objects.create(project=project, employee_id=employee_id)


@transaction.atomic
def remove_member(actor, project_id, *, employee_id):
    actor = lock_actor(actor, employee_id)
    project = _project(actor, project_id)
    _manage(actor, project)
    return ProjectMembership.objects.get(project=project, employee_id=employee_id).delete()


@transaction.atomic
def create_task(actor, project_id, **data):
    actor = lock_actor(actor, data.get("assignee_id"))
    project = _project(actor, project_id)
    _manage(actor, project)
    check_fields(data, {"title", "description", "assignee_id"})
    return Task.objects.create(project=project, **data)


@transaction.atomic
def update_task(actor, task_id, **data):
    actor = lock_actor(actor, data.get("assignee_id"))
    task = _task(actor, task_id)
    if actor.role == User.Role.EMPLOYEE:
        if task.assignee_id != actor.pk:
            raise PermissionDenied("Only the assigned employee can update task status.")
        allowed = {"status"}
    else:
        _manage(actor, task.project)
        allowed = {"title", "description", "assignee_id", "status"}
    check_fields(data, allowed)
    if task.status == Task.Status.COMPLETED:
        if data == {"status": Task.Status.COMPLETED}:
            return task
        raise PermissionDenied("Completed tasks are read-only; Admin must use a correction.")
    return _save(task, data)


@transaction.atomic
def correct_completed_task(actor, task_id, **data):
    actor = lock_actor(actor, data.get("assignee_id"))
    if actor.role != User.Role.ADMIN:
        raise PermissionDenied("Only Admin can correct completed tasks.")
    task = _task(actor, task_id)
    if task.status != Task.Status.COMPLETED:
        raise PermissionDenied("Use the normal update for unfinished tasks.")
    check_fields(data, {"title", "description", "assignee_id"})
    return _save(task, data)


@transaction.atomic
def delete_task(actor, task_id):
    actor = lock_actor(actor)
    task = _task(actor, task_id)
    _manage(actor, task.project)
    if task.status == Task.Status.COMPLETED:
        raise PermissionDenied("Completed tasks are retained; use Admin correction.")
    return task.delete()


def _own_time(actor, task, entry=None):
    if (
        actor.role != User.Role.EMPLOYEE
        or task.assignee_id != actor.pk
        or task.status != Task.Status.IN_PROGRESS
        or (entry is not None and entry.employee_id != actor.pk)
        or not ProjectMembership.objects.filter(project=task.project, employee=actor).exists()
    ):
        raise PermissionDenied("Time requires your own entry and assigned In progress task.")


@transaction.atomic
def create_time_entry(actor, task_id, **data):
    actor = lock_actor(actor)
    task = _task(actor, task_id)
    _own_time(actor, task)
    check_fields(data, {"work_date", "minutes", "note"})
    return TimeEntry.objects.create(task=task, employee=actor, **data)


def _entry(actor, entry_id):
    task_id = TimeEntry.objects.values_list("task_id", flat=True).get(pk=entry_id)
    task = _task(actor, task_id)
    return task, TimeEntry.objects.get(pk=entry_id, task=task)


@transaction.atomic
def update_time_entry(actor, entry_id, **data):
    actor = lock_actor(actor)
    task, entry = _entry(actor, entry_id)
    _own_time(actor, task, entry)
    check_fields(data, {"work_date", "minutes", "note"})
    return _save(entry, data)


@transaction.atomic
def delete_time_entry(actor, entry_id):
    actor = lock_actor(actor)
    task, entry = _entry(actor, entry_id)
    _own_time(actor, task, entry)
    return entry.delete()


@transaction.atomic
def correct_time_entry(actor, entry_id, **data):
    actor = lock_actor(actor)
    if actor.role != User.Role.ADMIN:
        raise PermissionDenied("Only Admin can correct historical time.")
    _, entry = _entry(actor, entry_id)
    check_fields(data, {"work_date", "minutes", "note"})
    return _save(entry, data)

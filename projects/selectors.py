"""Scope before filtering, fetching details, pagination or aggregation."""

from django.core.exceptions import PermissionDenied

from accounts.models import User
from accounts.services import require_actor
from projects.models import Project, Task, TimeEntry


def projects_for(actor):
    actor = require_actor(actor)
    if actor.role == User.Role.ADMIN:
        return Project.objects.all()
    if actor.role == User.Role.PROJECT_MANAGER:
        return Project.objects.filter(manager=actor)
    return Project.objects.filter(memberships__employee=actor)


def project_for(actor, project_id):
    return projects_for(actor).get(pk=project_id)


def tasks_for(actor):
    return Task.objects.filter(project__in=projects_for(actor))


def task_for(actor, task_id):
    return tasks_for(actor).get(pk=task_id)


def task_summaries_for(actor):
    return tasks_for(actor).values("id", "project_id", "title", "assignee_id", "status")


def time_entries_for(actor):
    actor = require_actor(actor)
    entries = TimeEntry.objects.filter(task__project__in=projects_for(actor))
    if actor.role == User.Role.EMPLOYEE:
        entries = entries.filter(employee=actor)
    return entries


def time_entry_for(actor, entry_id):
    return time_entries_for(actor).get(pk=entry_id)


def membership_options_for(actor, project_id):
    actor = require_actor(actor)
    project = project_for(actor, project_id)
    if actor.role != User.Role.ADMIN and not (
        actor.role == User.Role.PROJECT_MANAGER and project.manager_id == actor.pk
    ):
        raise PermissionDenied("Only Admin or the owning Manager can select new members.")
    return User.objects.filter(role=User.Role.EMPLOYEE, is_active=True)

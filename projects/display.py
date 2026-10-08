"""Scoped display data for desktop pages; existing reports remain the metrics source."""

from django.db.models import Sum

from accounts.models import User
from projects import reports, selectors
from projects.models import Task


def project_rows(actor, projects):
    return [
        {"project": project, "report": reports.project_report(actor, project.pk)}
        for project in projects
    ]


def dashboard(actor):
    summary = reports.overview_report(actor)
    tasks = selectors.tasks_for(actor)
    if actor.role == User.Role.EMPLOYEE:
        tasks = tasks.filter(assignee=actor).exclude(status=Task.Status.COMPLETED)
    else:
        tasks = tasks.filter(status=Task.Status.IN_PROGRESS)
    tasks = list(tasks.select_related("project", "assignee").order_by("pk")[:10])
    return {
        "summary": summary,
        "unfinished": summary["total_tasks"] - summary["completed_tasks"],
        "employee_count": User.objects.filter(role=User.Role.EMPLOYEE).count()
        if actor.role == User.Role.ADMIN
        else None,
        "task_rows": task_rows(actor, tasks),
    }


def task_rows(actor, tasks):
    tasks = list(tasks)
    minutes = dict(
        selectors.time_entries_for(actor)
        .filter(task_id__in=[t.pk for t in tasks])
        .values("task_id")
        .annotate(total=Sum("minutes"))
        .values_list("task_id", "total")
    )
    return [{"task": task, "minutes": minutes.get(task.pk, 0)} for task in tasks]

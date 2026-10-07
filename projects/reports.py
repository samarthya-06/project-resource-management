"""Role-scoped counts and time, aggregated separately to avoid join multiplication."""

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Sum

from accounts.models import User
from accounts.services import require_actor
from projects import selectors
from projects.models import Task


def rounded_ratio(numerator, denominator):
    return float(
        (Decimal(numerator) / Decimal(denominator)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )


def _metrics(tasks, entries):
    counts = {status: 0 for status in Task.Status.values}
    counts.update(
        {row["status"]: row["total"] for row in tasks.values("status").annotate(total=Count("pk"))}
    )
    total = sum(counts.values())
    completed = counts[Task.Status.COMPLETED]
    minutes = entries.aggregate(total=Sum("minutes"))["total"] or 0
    return {
        "task_counts": counts,
        "total_tasks": total,
        "completed_tasks": completed,
        "completion_percentage": rounded_ratio(100 * completed, total) if total else 0,
        "total_minutes": minutes,
        "total_hours": rounded_ratio(minutes, 60),
    }


def project_report(actor, project_id):
    actor = require_actor(actor)
    project = selectors.project_for(actor, project_id)
    tasks = selectors.tasks_for(actor).filter(project=project)
    entries = selectors.time_entries_for(actor).filter(task__project=project)
    own = actor.role == User.Role.EMPLOYEE
    if own:
        tasks = tasks.filter(assignee=actor)
    contributors = (
        entries.values(
            "employee_id", "employee__first_name", "employee__last_name", "employee__username"
        )
        .annotate(minutes=Sum("minutes"))
        .order_by("employee_id")
    )
    return {
        "project_id": project.pk,
        "scope": "own_work" if own else "project",
        "scope_label": "Own work" if own else "Project work",
        **_metrics(tasks, entries),
        "contributors": [
            {
                "employee_id": row["employee_id"],
                "name": (row["employee__first_name"] + " " + row["employee__last_name"]).strip()
                or row["employee__username"],
                "minutes": row["minutes"],
                "hours": rounded_ratio(row["minutes"], 60),
            }
            for row in contributors
        ],
    }


def overview_report(actor):
    actor = require_actor(actor)
    projects = selectors.projects_for(actor)
    tasks = selectors.tasks_for(actor)
    entries = selectors.time_entries_for(actor)
    own = actor.role == User.Role.EMPLOYEE
    if own:
        tasks = tasks.filter(assignee=actor)
    return {
        "scope": "own_work" if own else "authorized_projects",
        "scope_label": "Own work in membership projects" if own else "Authorized project work",
        "project_count": projects.count(),
        **_metrics(tasks, entries),
    }

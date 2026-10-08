"""Desktop task/time adapters. Shared services authorize and validate every write."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import User
from projects import display, reports, selectors, services
from projects.forms import (
    ConfirmationForm,
    MyTaskFilterForm,
    OperationForm,
    TaskFilterForm,
    TaskForm,
    TimeForm,
)
from projects.models import Task
from projects.ui_helpers import available, manageable_project, page_actor, save_form


def save_operation(form, operation, *args, **data):
    """Retain submitted values when fresh service state rejects a stale form."""
    try:
        return save_form(form, operation, *args, **data), 200
    except PermissionDenied:
        form.add_error(
            None,
            "This change is no longer permitted. The task may have been completed or reassigned. "
            "Refresh the task; contact an Admin if a correction is needed.",
        )
        return False, 403


def status_actor(actor, task):
    if actor.role == User.Role.EMPLOYEE and task.assignee_id != actor.pk:
        raise PermissionDenied


def own_time_actor(actor, task, entry=None, check_state=True):
    if actor.role != User.Role.EMPLOYEE or (entry and entry.employee_id != actor.pk):
        raise PermissionDenied
    if check_state and (task.assignee_id != actor.pk or task.status != Task.Status.IN_PROGRESS):
        raise PermissionDenied


def list_context(request, actor, tasks, form):
    valid = form.is_valid()
    if valid:
        data = form.cleaned_data
        status = data.get("status")
        if status == "unfinished":
            tasks = tasks.exclude(status=Task.Status.COMPLETED)
        elif status:
            tasks = tasks.filter(status=status)
        for field in ["assignee", "project"]:
            if data.get(field):
                tasks = tasks.filter(**{field: data[field]})
    else:
        tasks = tasks.none()
    page = Paginator(tasks.select_related("project", "assignee").order_by("pk"), 25).get_page(
        request.GET.get("page")
    )
    query = request.GET.copy()
    query.pop("page", None)
    return {
        "actor": actor,
        "form": form,
        "page": page,
        "task_rows": display.task_rows(actor, page),
        "filter_query": query.urlencode(),
    }, 200 if valid else 400


@never_cache
@require_GET
def project_tasks(request, project_id):
    actor = page_actor(request)
    project = available(selectors.project_for, actor, project_id)
    context, code = list_context(
        request,
        actor,
        selectors.tasks_for(actor).filter(project=project),
        TaskFilterForm(request.GET, project=project),
    )
    context.update(
        nav="projects",
        section="tasks",
        project=project,
        report=reports.project_report(actor, project.pk),
    )
    return render(request, "workspace/project_tasks.html", context, status=code)


@never_cache
@require_GET
def my_tasks(request):
    actor = page_actor(request)
    if actor.role != User.Role.EMPLOYEE:
        raise PermissionDenied
    query = request.GET.copy()
    if "status" not in query:
        query["status"] = "unfinished"
    form = MyTaskFilterForm(query, projects=selectors.projects_for(actor))
    context, code = list_context(
        request, actor, selectors.tasks_for(actor).filter(assignee=actor), form
    )
    context.update(nav="tasks", summary=reports.overview_report(actor))
    return render(request, "workspace/my_tasks.html", context, status=code)


@never_cache
@require_http_methods(["GET", "POST"])
def task_form(request, project_id=None, task_id=None, correction=False):
    actor = page_actor(request)
    task = available(selectors.task_for, actor, task_id) if task_id else None
    project = manageable_project(actor, task.project_id if task else project_id)
    if correction:
        if actor.role != User.Role.ADMIN or task.status != Task.Status.COMPLETED:
            raise PermissionDenied
    elif task and task.status == Task.Status.COMPLETED and request.method == "GET":
        raise PermissionDenied
    form = TaskForm(request.POST if request.method == "POST" else None, project=project, task=task)
    code = 200
    if request.method == "POST" and form.is_valid():
        operation = (
            services.correct_completed_task
            if correction
            else services.update_task
            if task
            else services.create_task
        )
        saved, code = save_operation(
            form, operation, actor, task.pk if task else project.pk, **form.service_data()
        )
        if saved:
            messages.success(
                request,
                "Completed task corrected; status retained."
                if correction
                else "Task saved."
                if task
                else "Task created.",
            )
            return (
                redirect("projects:task_detail", task_id=task.pk)
                if task
                else redirect("projects:tasks", project_id=project.pk)
            )
    return render(
        request,
        "workspace/task_form.html",
        {
            "actor": actor,
            "nav": "projects",
            "project": project,
            "task": task,
            "form": form,
            "correction": correction,
        },
        status=code,
    )


def detail_context(actor, task, form=None):
    entries = (
        selectors.time_entries_for(actor)
        .filter(task=task)
        .select_related("employee")
        .order_by("-work_date", "-pk")
    )
    can_work = actor.role == User.Role.EMPLOYEE and task.assignee_id == actor.pk
    return {
        "actor": actor,
        "nav": "tasks" if actor.role == User.Role.EMPLOYEE else "projects",
        "task": task,
        "entries": entries,
        "total_minutes": entries.aggregate(total=Sum("minutes"))["total"] or 0,
        "can_status": actor.role != User.Role.EMPLOYEE or can_work,
        "can_time": can_work and task.status == Task.Status.IN_PROGRESS,
        "has_history": task.time_entries.exists(),
        "form": form or TimeForm(),
    }


@never_cache
@require_GET
def task_detail(request, task_id):
    actor = page_actor(request)
    task = available(selectors.task_for, actor, task_id)
    return render(request, "workspace/task_detail.html", detail_context(actor, task))


@never_cache
@require_POST
def task_start(request, task_id):
    actor = page_actor(request)
    task = available(selectors.task_for, actor, task_id)
    status_actor(actor, task)
    form = OperationForm(request.POST)
    code = 200
    if form.is_valid():
        saved, code = save_operation(
            form, services.update_task, actor, task.pk, status=Task.Status.IN_PROGRESS
        )
        if saved:
            messages.success(request, "Task started. You can now record your work.")
            return redirect("projects:task_detail", task_id=task.pk)
    context = detail_context(actor, task)
    context["action_form"] = form
    return render(request, "workspace/task_detail.html", context, status=code)


@never_cache
@require_http_methods(["GET", "POST"])
def task_confirm(request, task_id, deletion=False):
    actor = page_actor(request)
    task = available(selectors.task_for, actor, task_id)
    status_actor(actor, task)
    if deletion and actor.role == User.Role.EMPLOYEE:
        raise PermissionDenied
    if request.method == "GET" and (
        task.status == Task.Status.COMPLETED
        or (not deletion and task.status != Task.Status.IN_PROGRESS)
    ):
        raise PermissionDenied
    form = ConfirmationForm(request.POST if request.method == "POST" else None)
    code = 200
    if request.method == "POST" and form.is_valid():
        if deletion:
            saved, code = save_operation(form, services.delete_task, actor, task.pk)
        else:
            saved, code = save_operation(
                form, services.update_task, actor, task.pk, status=Task.Status.COMPLETED
            )
        if saved:
            messages.success(
                request,
                "Task deleted."
                if deletion
                else "Task completed. Recorded work is now read-only for Employees and Managers.",
            )
            return (
                redirect("projects:tasks", project_id=task.project_id)
                if deletion
                else redirect("projects:task_detail", task_id=task.pk)
            )
    return render(
        request,
        "workspace/confirmation.html",
        {
            "actor": actor,
            "nav": "tasks" if actor.role == User.Role.EMPLOYEE else "projects",
            "title": "Delete task" if deletion else "Mark completed",
            "item_name": task.title,
            "form": form,
            "button_class": "danger" if deletion else "primary",
            "cancel_url": reverse("projects:task_detail", args=[task.pk]),
            "explanation": "Only unfinished tasks with no recorded time can be deleted."
            if deletion
            else "Record any remaining time first. Completed tasks and their time entries become "
            "read-only for Employees and Managers. An Admin can make an explicit correction "
            "without reopening the task.",
        },
        status=code,
    )


@never_cache
@require_http_methods(["GET", "POST"])
def time_form(request, task_id=None, entry_id=None, correction=False):
    actor = page_actor(request)
    entry = available(selectors.time_entry_for, actor, entry_id) if entry_id else None
    task = available(selectors.task_for, actor, entry.task_id if entry else task_id)
    if correction:
        if actor.role != User.Role.ADMIN:
            raise PermissionDenied
    else:
        own_time_actor(actor, task, entry, check_state=request.method == "GET")
    form = TimeForm(request.POST if request.method == "POST" else None, entry=entry)
    code = 200
    if request.method == "POST" and form.is_valid():
        operation = (
            services.correct_time_entry
            if correction
            else services.update_time_entry
            if entry
            else services.create_time_entry
        )
        saved, code = save_operation(
            form, operation, actor, entry.pk if entry else task.pk, **form.cleaned_data
        )
        if saved:
            messages.success(
                request,
                "Time corrected. Original contributor and task status retained."
                if correction
                else "Time saved."
                if entry
                else "Time logged.",
            )
            return redirect("projects:task_detail", task_id=task.pk)
    return render(
        request,
        "workspace/time_form.html",
        {
            "actor": actor,
            "nav": "tasks" if actor.role == User.Role.EMPLOYEE else "projects",
            "task": task,
            "entry": entry,
            "form": form,
            "correction": correction,
        },
        status=code,
    )


@never_cache
@require_http_methods(["GET", "POST"])
def time_delete(request, entry_id):
    actor = page_actor(request)
    entry = available(selectors.time_entry_for, actor, entry_id)
    task = available(selectors.task_for, actor, entry.task_id)
    own_time_actor(actor, task, entry, check_state=request.method == "GET")
    form = ConfirmationForm(request.POST if request.method == "POST" else None)
    code = 200
    if request.method == "POST" and form.is_valid():
        saved, code = save_operation(form, services.delete_time_entry, actor, entry.pk)
        if saved:
            messages.success(request, "Time entry deleted.")
            return redirect("projects:task_detail", task_id=task.pk)
    return render(
        request,
        "workspace/confirmation.html",
        {
            "actor": actor,
            "nav": "tasks",
            "form": form,
            "title": "Delete time entry",
            "item_name": f"{task.title} · {entry.work_date:%d %b %Y} · {entry.minutes} minutes",
            "explanation": "This removes your selected entry and note from recorded totals. "
            "It cannot be undone.",
            "cancel_url": reverse("projects:task_detail", args=[task.pk]),
        },
        status=code,
    )

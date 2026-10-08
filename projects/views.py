from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from accounts.models import User
from projects import display, reports, selectors, services
from projects.forms import ConfirmationForm, MemberForm, ProjectForm
from projects.models import Task
from projects.ui_helpers import available, manageable_project, page_actor, save_form


@never_cache
@require_GET
def overview(request):
    actor = page_actor(request)
    return render(
        request,
        "workspace/overview.html",
        {"actor": actor, "nav": "overview", **display.dashboard(actor)},
    )


@never_cache
@require_GET
def project_list(request):
    actor = page_actor(request)
    query = request.GET.get("q", "").strip()
    projects = selectors.projects_for(actor).select_related("manager").order_by("pk")
    if query:
        projects = projects.filter(name__icontains=query)
    page = Paginator(projects, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "workspace/projects.html",
        {
            "actor": actor,
            "nav": "projects",
            "q": query,
            "page": page,
            "rows": display.project_rows(actor, page),
            "summary": reports.overview_report(actor),
        },
    )


@never_cache
@require_http_methods(["GET", "POST"])
def project_form(request, project_id=None):
    actor = page_actor(request)
    if actor.role == User.Role.EMPLOYEE:
        raise PermissionDenied
    project = manageable_project(actor, project_id) if project_id else None
    form = ProjectForm(
        request.POST if request.method == "POST" else None, actor=actor, project=project
    )
    if request.method == "POST" and form.is_valid():
        if project:
            saved = save_form(
                form, services.update_project, actor, project.pk, **form.service_data()
            )
        else:
            saved = save_form(form, services.create_project, actor, **form.service_data())
        if saved:
            messages.success(request, "Project saved." if project else "Project created.")
            return (
                redirect("projects:detail", project_id=project.pk)
                if project
                else redirect("projects:list")
            )
    return render(
        request,
        "workspace/project_form.html",
        {"actor": actor, "nav": "projects", "form": form, "project": project},
    )


@never_cache
@require_GET
def project_detail(request, project_id, section="overview"):
    actor = page_actor(request)
    project = available(selectors.project_for, actor, project_id)
    members = list(project.memberships.select_related("employee").order_by("pk"))
    team = [
        {
            "membership": member,
            "unfinished": project.tasks.filter(assignee_id=member.employee_id)
            .exclude(status=Task.Status.COMPLETED)
            .count(),
        }
        for member in members
    ]
    return render(
        request,
        "workspace/project_detail.html",
        {
            "actor": actor,
            "nav": "projects",
            "project": project,
            "section": section,
            "report": reports.project_report(actor, project.pk),
            "team": team,
        },
    )


@never_cache
@require_http_methods(["GET", "POST"])
def member_add(request, project_id):
    actor = page_actor(request)
    project = manageable_project(actor, project_id)
    form = MemberForm(
        request.POST if request.method == "POST" else None, actor=actor, project=project
    )
    if request.method == "POST" and form.is_valid():
        if save_form(
            form,
            services.add_member,
            actor,
            project.pk,
            employee_id=form.cleaned_data["employee_id"].pk,
        ):
            messages.success(request, "Employee added to the project.")
            return redirect("projects:team", project_id=project.pk)
    return render(
        request,
        "workspace/member_form.html",
        {"actor": actor, "nav": "projects", "project": project, "form": form},
    )


@never_cache
@require_http_methods(["GET", "POST"])
def member_remove(request, project_id, employee_id):
    actor = page_actor(request)
    project = manageable_project(actor, project_id)
    member = project.memberships.select_related("employee").filter(employee_id=employee_id).first()
    if member is None:
        raise Http404
    form = ConfirmationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        if save_form(form, services.remove_member, actor, project.pk, employee_id=employee_id):
            messages.success(request, "Employee removed. Recorded work history is preserved.")
            return redirect("projects:team", project_id=project.pk)
    return render(
        request,
        "workspace/confirmation.html",
        {
            "actor": actor,
            "nav": "projects",
            "title": "Remove employee",
            "item_name": member.employee.get_full_name() or member.employee.username,
            "explanation": (
                "Recorded time stays with its original contributor. "
                "Reassign or complete unfinished tasks before removing this member."
            ),
            "form": form,
            "cancel_url": f"/projects/{project.pk}/team/",
        },
    )

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from accounts import selectors, services
from accounts.workspace_forms import AccountForm
from projects.forms import ConfirmationForm
from projects.ui_helpers import available, page_actor, save_form


@never_cache
@require_GET
def employee_list(request):
    actor = page_actor(request)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    accounts = selectors.accounts_for(actor).order_by("pk")
    if query:
        accounts = accounts.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
        )
    if status in {"active", "inactive"}:
        accounts = accounts.filter(is_active=status == "active")
    page = Paginator(accounts, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "workspace/employees.html",
        {"actor": actor, "nav": "employees", "q": query, "status_filter": status, "page": page},
    )


@never_cache
@require_http_methods(["GET", "POST"])
def employee_form(request, account_id=None):
    actor = page_actor(request)
    accounts = selectors.accounts_for(actor)
    account = available(accounts.get, pk=account_id) if account_id else None
    form = AccountForm(request.POST if request.method == "POST" else None, account=account)
    if request.method == "POST" and form.is_valid():
        if account:
            saved = save_form(
                form, services.update_account, actor, account.pk, **form.service_data()
            )
        else:
            saved = save_form(form, services.create_account, actor, **form.service_data())
        if saved:
            messages.success(
                request,
                "Account saved."
                if account
                else (
                    "Account created. Share the initial password privately; "
                    "a password change is required."
                ),
            )
            return redirect("accounts:employees")
    return render(
        request,
        "workspace/employee_form.html",
        {"actor": actor, "nav": "employees", "form": form, "account": account},
    )


@never_cache
@require_http_methods(["GET", "POST"])
def employee_deactivate(request, account_id):
    actor = page_actor(request)
    account = available(selectors.accounts_for(actor).get, pk=account_id)
    form = ConfirmationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        if save_form(form, services.deactivate_account, actor, account.pk):
            messages.success(request, "Account deactivated. Work history is preserved.")
            return redirect("accounts:employees")
    return render(
        request,
        "workspace/confirmation.html",
        {
            "actor": actor,
            "nav": "employees",
            "title": "Deactivate account",
            "item_name": account.get_full_name() or account.username,
            "explanation": (
                "This account will no longer be able to sign in or receive new "
                "assignments. Projects, tasks and recorded time are preserved."
            ),
            "form": form,
            "cancel_url": "/employees/",
        },
    )

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .forms import LoginForm


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.must_change_password:
            return str(reverse_lazy("accounts:password_change"))
        return super().get_success_url()


class ChangePasswordView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:overview")

    def form_valid(self, form):
        with transaction.atomic():
            user = form.save(commit=False)
            user.must_change_password = False
            user.save(update_fields=["password", "must_change_password"])
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Your password has been changed.")
        return redirect(self.success_url)


@never_cache
@require_GET
def overview(request):
    return render(request, "accounts/overview.html")


@api_view(["GET"])
def current_user(request):
    """Read-only identity; no client-controlled role or account updates."""
    user = request.user
    response = Response(
        {
            "id": user.pk,
            "username": user.username,
            "name": user.get_full_name() or user.username,
            "role": user.role,
            "role_label": user.get_role_display(),
        }
    )
    response["Cache-Control"] = "no-store"
    return response

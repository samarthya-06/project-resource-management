from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin


class InitialPasswordMiddleware(MiddlewareMixin):
    """Initial credentials only allow password change and logout."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated or not request.user.must_change_password:
            return None
        if request.resolver_match.view_name in {
            "accounts:login",
            "accounts:password_change",
            "accounts:logout",
        }:
            return None
        if request.path.startswith("/api/"):
            return JsonResponse(
                {"detail": "Change your initial password before using the API."}, status=403
            )
        return redirect("accounts:password_change")

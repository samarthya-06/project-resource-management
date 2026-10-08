from django.contrib.auth.views import LogoutView
from django.urls import path

from projects import views as workspace

from . import views, workspace_views

app_name = "accounts"
urlpatterns = [
    path("", workspace.overview, name="overview"),
    path("employees/", workspace_views.employee_list, name="employees"),
    path("employees/create/", workspace_views.employee_form, name="employee_create"),
    path("employees/<int:account_id>/edit/", workspace_views.employee_form, name="employee_edit"),
    path(
        "employees/<int:account_id>/deactivate/",
        workspace_views.employee_deactivate,
        name="employee_deactivate",
    ),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/change/", views.ChangePasswordView.as_view(), name="password_change"),
]

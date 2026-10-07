from django.urls import include, path
from rest_framework.routers import SimpleRouter

from accounts.api import AccountViewSet
from projects.api import (
    EmployeePicker,
    MembershipViewSet,
    Overview,
    ProjectViewSet,
    TaskViewSet,
    TimeEntryViewSet,
)

router = SimpleRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("projects", ProjectViewSet, basename="project")
router.register("tasks", TaskViewSet, basename="task")
router.register("time-entries", TimeEntryViewSet, basename="time-entry")

urlpatterns = [
    path("", include(router.urls)),
    path("overview/", Overview.as_view(), name="overview-report"),
    path(
        "projects/<int:project_id>/memberships/",
        MembershipViewSet.as_view({"get": "list", "post": "create"}),
        name="memberships",
    ),
    path(
        "projects/<int:project_id>/memberships/<int:employee_id>/",
        MembershipViewSet.as_view({"delete": "destroy"}),
        name="membership-remove",
    ),
    path(
        "projects/<int:project_id>/employee-options/",
        EmployeePicker.as_view(),
        name="employee-options",
    ),
]

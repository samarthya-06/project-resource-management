from django.contrib import admin
from django.urls import include, path

from accounts.views import current_user

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/me/", current_user, name="current_user"),
    path("api/", include("projects.api_urls")),
    path("", include("accounts.urls")),
]

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User


class AccountCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "role")


class AccountChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class AccountAdmin(UserAdmin):
    form = AccountChangeForm
    add_form = AccountCreationForm
    list_display = ("username", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Workspace", {"fields": ("role", "must_change_password")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Workspace", {"fields": ("first_name", "last_name", "email", "role")}),
    )

    def has_module_permission(self, request):
        return (
            request.user.is_active
            and request.user.is_superuser
            and request.user.role == User.Role.ADMIN
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def user_change_password(self, request, id, form_url=""):
        response = super().user_change_password(request, id, form_url)
        if (
            request.method == "POST"
            and response.status_code == 302
            and str(request.user.pk) != str(id)
        ):
            User.objects.filter(pk=id).update(must_change_password=True)
        return response

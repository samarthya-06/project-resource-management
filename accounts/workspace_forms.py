from django import forms

from accounts.models import User
from projects.forms import OperationForm


class AccountForm(OperationForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    username = forms.CharField(label="Login identifier", max_length=150)
    email = forms.EmailField(required=False)
    role = forms.ChoiceField(
        choices=User.Role.choices,
        initial=User.Role.EMPLOYEE,
        help_text="Give only the access needed for this account's work.",
    )
    password = forms.CharField(
        label="Initial password",
        strip=False,
        widget=forms.PasswordInput,
        help_text=(
            "Share this password privately. The account must change it before using the workspace."
        ),
    )
    confirm_role = forms.BooleanField(required=False, label="I confirm this change of role.")

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = account
        if account:
            self.initial.update(
                {
                    field: getattr(account, field)
                    for field in ["username", "email", "first_name", "last_name", "role"]
                }
            )
            self.fields["password"].required = False
            self.fields["password"].label = "Reset password (optional)"
            self.fields["password"].help_text = (
                "Leave blank to keep the password. Share a reset privately; "
                "a password change is required at next sign-in."
            )
        else:
            del self.fields["confirm_role"]

    def clean(self):
        data = super().clean()
        if (
            self.account
            and data.get("role", self.account.role) != self.account.role
            and not data.get("confirm_role")
        ):
            self.add_error("confirm_role", "Confirm the role change before saving.")
        return data

    def service_data(self):
        data = dict(self.cleaned_data)
        data.pop("confirm_role", None)
        if self.account and not data.get("password"):
            data.pop("password", None)
        return data

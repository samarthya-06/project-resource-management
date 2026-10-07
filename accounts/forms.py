from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "The login identifier or password is incorrect.",
        "inactive": "The login identifier or password is incorrect.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Login identifier"
        self.fields["username"].widget.attrs.update({"autocomplete": "username", "autofocus": True})

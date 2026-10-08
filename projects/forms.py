from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from projects.models import Project, Task
from projects.selectors import membership_options_for


class OperationForm(forms.Form):
    def clean(self):
        data = super().clean()
        unknown = set(self.data) - set(self.fields) - {"csrfmiddlewaretoken"}
        if unknown:
            raise ValidationError("The request contains fields that cannot be changed here.")
        return data


class NamedUserChoice(forms.ModelChoiceField):
    def label_from_instance(self, user):
        return user.get_full_name() or user.username


class ProjectForm(OperationForm):
    name = forms.CharField(label="Project name", max_length=200)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    def __init__(self, *args, actor, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if actor.role == User.Role.ADMIN:
            managers = User.objects.filter(role=User.Role.PROJECT_MANAGER, is_active=True)
            if project:
                managers = User.objects.filter(pk__in=managers.values("pk")) | User.objects.filter(
                    pk=project.manager_id
                )
            self.fields["manager_id"] = NamedUserChoice(
                label="Project manager", queryset=managers.order_by("first_name", "pk")
            )
            if project:
                self.initial["manager_id"] = project.manager_id
        if project:
            for name in ["name", "description", "start_date", "end_date"]:
                self.initial[name] = getattr(project, name)

    def service_data(self):
        data = dict(self.cleaned_data)
        if "manager_id" in data:
            data["manager_id"] = data["manager_id"].pk
        return data


class MemberForm(OperationForm):
    employee_id = NamedUserChoice(label="Employee", queryset=User.objects.none())

    def __init__(self, *args, actor, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_id"].queryset = (
            membership_options_for(actor, project.pk)
            .order_by("first_name", "pk")
            .exclude(pk__in=project.memberships.values("employee_id"))
        )


class ConfirmationForm(OperationForm):
    confirm = forms.BooleanField(label="I confirm this action.")


class TaskForm(OperationForm):
    title = forms.CharField(label="Task title", max_length=200)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    assignee_id = NamedUserChoice(label="Assignee", queryset=User.objects.none())

    def __init__(self, *args, project, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        members = User.objects.filter(
            project_memberships__project=project, role=User.Role.EMPLOYEE, is_active=True
        ).order_by("first_name", "pk")
        self.fields["assignee_id"].queryset = members
        self.fields[
            "assignee_id"
        ].help_text = "Only active project members can receive assignments."
        if task:
            self.initial.update(title=task.title, description=task.description)
            self.fields["assignee_id"].required = False
            self.fields["assignee_id"].empty_label = "Keep current assignee"
            self.fields["assignee_id"].help_text += " Leave blank to keep the current assignee."
            if members.filter(pk=task.assignee_id).exists():
                self.initial["assignee_id"] = task.assignee_id

    def service_data(self):
        data = dict(self.cleaned_data)
        assignee = data.pop("assignee_id")
        if assignee:
            data["assignee_id"] = assignee.pk
        return data


class TimeForm(OperationForm):
    work_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text="No future dates.",
    )
    hours = forms.IntegerField(min_value=0, max_value=24, initial=0, help_text="Whole hours.")
    minutes = forms.IntegerField(
        min_value=0, max_value=59, initial=0, help_text="Additional minutes, from 0 to 59."
    )
    note = forms.CharField(
        label="Work note", required=False, widget=forms.Textarea(attrs={"rows": 2})
    )

    def __init__(self, *args, entry=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work_date"].widget.attrs["max"] = timezone.localdate().isoformat()
        self.initial["work_date"] = timezone.localdate()
        if entry:
            hours, minutes = divmod(entry.minutes, 60)
            self.initial.update(
                work_date=entry.work_date, hours=hours, minutes=minutes, note=entry.note
            )

    def clean(self):
        data = super().clean()
        if "hours" in data and "minutes" in data:
            total = data["hours"] * 60 + data["minutes"]
            if not 1 <= total <= 1440:
                raise ValidationError("Enter a duration from 1 minute to 24 hours.")
        return data

    def service_data(self):
        data = dict(self.cleaned_data)
        data["minutes"] += data.pop("hours") * 60
        return data


class TaskFilterForm(forms.Form):
    status = forms.ChoiceField(required=False, choices=[("", "All statuses"), *Task.Status.choices])
    assignee = NamedUserChoice(
        required=False, queryset=User.objects.none(), empty_label="All assignees"
    )

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = (
            User.objects.filter(
                Q(project_memberships__project=project) | Q(assigned_tasks__project=project)
            )
            .distinct()
            .order_by("first_name", "pk")
        )


class MyTaskFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=[("unfinished", "Unfinished"), ("", "All statuses"), *Task.Status.choices],
    )
    project = forms.ModelChoiceField(
        required=False, queryset=Project.objects.none(), empty_label="All membership projects"
    )

    def __init__(self, *args, projects, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = projects.order_by("pk")

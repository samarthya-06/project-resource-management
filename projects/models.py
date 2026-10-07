from copy import copy
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, router, transaction
from django.utils import timezone

from accounts.models import User


class ValidatedModel(models.Model):
    """Explicitly validate ordinary saves, including the effective partial update."""

    class Meta:
        abstract = True

    def project_lock_id(self, using):
        return self.project_id

    def save(self, *args, **kwargs):
        using = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            if not update_fields:
                return
            kwargs["update_fields"] = update_fields
        with transaction.atomic(using=using):
            # Every ordinary mutation locks the containing project first. This
            # also serializes task assignment with guarded membership removal.
            project_id = self.project_lock_id(using)
            if project_id:
                Project.objects.using(using).select_for_update().filter(pk=project_id).first()
            previous = None
            if not self._state.adding:
                previous = type(self).objects.using(using).select_for_update().get(pk=self.pk)
            candidate = self
            if previous is not None and update_fields is not None:
                candidate = previous
                writable = {f.name: f for f in self._meta.concrete_fields if not f.primary_key}
                writable.update({f.attname: f for f in writable.values()})
                for name in update_fields:
                    if name not in writable:
                        raise ValueError(f"Unknown or non-writable update field: {name}")
                    field = writable[name]
                    setattr(candidate, field.attname, getattr(self, field.attname))
            candidate._state = copy(candidate._state)
            candidate._state.db = using
            candidate.full_clean()
            models.Model.save(candidate, *args, **kwargs)
            self.pk = candidate.pk
            self._state = candidate._state


class Project(ValidatedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_projects"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    demo_key = models.CharField(max_length=64, null=True, blank=True, unique=True, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"), name="project_name_not_blank"
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="project_dates_ordered",
            ),
        ]

    def project_lock_id(self, using):
        return self.pk if not self._state.adding else None

    def clean(self):
        super().clean()
        previous = None
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db).get(pk=self.pk)
            if self.demo_key != previous.demo_key:
                raise ValidationError({"demo_key": "The demo identity cannot be changed."})
        if previous is None or self.manager_id != previous.manager_id:
            if (
                not User.objects.using(self._state.db)
                .filter(pk=self.manager_id, role=User.Role.PROJECT_MANAGER, is_active=True)
                .exists()
            ):
                raise ValidationError({"manager": "Choose an active Project Manager."})
        if (
            isinstance(self.start_date, date)
            and isinstance(self.end_date, date)
            and self.end_date < self.start_date
        ):
            raise ValidationError({"end_date": "End date must be on or after start date."})

    def __str__(self):
        return self.name


class MembershipQuerySet(models.QuerySet):
    def delete(self):
        using = self.db
        with transaction.atomic(using=using):
            selected = list(self.values_list("pk", "project_id"))
            if not selected:
                return 0, {}
            selected_ids = [pk for pk, _ in selected]
            project_ids = sorted({project_id for _, project_id in selected})
            list(
                Project.objects.using(using)
                .select_for_update()
                .filter(pk__in=project_ids)
                .order_by("pk")
            )
            # Re-read after the project locks; another assignment may have
            # finished while this deletion waited.
            memberships = list(self.filter(pk__in=selected_ids).select_for_update().order_by("pk"))
            for membership in memberships:
                if (
                    Task.objects.using(using)
                    .filter(project_id=membership.project_id, assignee_id=membership.employee_id)
                    .exclude(status=Task.Status.COMPLETED)
                    .exists()
                ):
                    raise ValidationError(
                        "Reassign or complete unfinished tasks before removing this member."
                    )
            return models.QuerySet.delete(self.filter(pk__in=[m.pk for m in memberships]))


class ProjectMembership(ValidatedModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="memberships")
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_memberships"
    )
    objects = MembershipQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "employee"], name="unique_project_employee"),
        ]

    def clean(self):
        super().clean()
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db).get(pk=self.pk)
            if (self.project_id, self.employee_id) != (previous.project_id, previous.employee_id):
                raise ValidationError(
                    "Remove a membership and add a new one to change its identity."
                )
        elif (
            not User.objects.using(self._state.db)
            .filter(pk=self.employee_id, role=User.Role.EMPLOYEE, is_active=True)
            .exists()
        ):
            raise ValidationError({"employee": "Choose an active Employee."})

    def delete(self, using=None, keep_parents=False):
        using = using or router.db_for_write(type(self), instance=self)
        result = type(self).objects.using(using).filter(pk=self.pk).delete()
        self.pk = None
        return result


class Task(ValidatedModel):
    class Status(models.TextChoices):
        TODO = "TODO", "To do"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_tasks"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(title__regex=r"\S"), name="task_title_not_blank"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["TODO", "IN_PROGRESS", "COMPLETED"]),
                name="task_valid_status",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status"], name="task_project_status_idx"),
            models.Index(fields=["assignee", "status"], name="task_assignee_status_idx"),
        ]

    def clean(self):
        super().clean()
        previous = None
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db).get(pk=self.pk)
            if self.project_id != previous.project_id:
                raise ValidationError(
                    {"project": "An existing task cannot move to another project."}
                )
            allowed = {
                self.Status.TODO: {self.Status.TODO, self.Status.IN_PROGRESS},
                self.Status.IN_PROGRESS: {self.Status.IN_PROGRESS, self.Status.COMPLETED},
                self.Status.COMPLETED: {self.Status.COMPLETED},
            }
            if self.status not in allowed[previous.status]:
                raise ValidationError(
                    {"status": "Move forward one step; completed tasks cannot reopen."}
                )
        elif self.status != self.Status.TODO:
            raise ValidationError({"status": "New tasks must begin at To do."})
        new_assignment = previous is None or self.assignee_id != previous.assignee_id
        if (
            new_assignment
            and not User.objects.using(self._state.db)
            .filter(pk=self.assignee_id, role=User.Role.EMPLOYEE, is_active=True)
            .exists()
        ):
            raise ValidationError({"assignee": "Choose an active Employee."})
        # A completed task may retain an assignee who later leaves the team.
        if new_assignment or self.status != self.Status.COMPLETED:
            if (
                not ProjectMembership.objects.using(self._state.db)
                .filter(project_id=self.project_id, employee_id=self.assignee_id)
                .exists()
            ):
                raise ValidationError(
                    {"assignee": "Choose an employee who belongs to this project."}
                )

    def __str__(self):
        return self.title


class TimeEntry(ValidatedModel):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="time_entries")
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="time_entries"
    )
    work_date = models.DateField()
    minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1440)]
    )
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(minutes__gte=1, minutes__lte=1440),
                name="time_minutes_bounded",
            ),
        ]

    def project_lock_id(self, using):
        return (
            Task.objects.using(using)
            .filter(pk=self.task_id)
            .values_list("project_id", flat=True)
            .first()
        )

    def clean_fields(self, exclude=None):
        # Django IntegerField otherwise truncates floating-point input before
        # validators see it. Forms/services must pass actual whole-minute ints.
        if "minutes" not in (exclude or ()) and type(self.minutes) is not int:
            raise ValidationError({"minutes": "Enter a positive number of whole minutes."})
        super().clean_fields(exclude=exclude)

    def clean(self):
        super().clean()
        if isinstance(self.work_date, date) and self.work_date > timezone.localdate():
            raise ValidationError({"work_date": "Work date cannot be in the future."})
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db).get(pk=self.pk)
            if (self.task_id, self.employee_id) != (previous.task_id, previous.employee_id):
                raise ValidationError("The original task and contributing employee cannot change.")
            return
        task = Task.objects.using(self._state.db).filter(pk=self.task_id).first()
        if task is None:
            return  # Foreign-key field validation supplies the missing-task error.
        if task.status != Task.Status.IN_PROGRESS:
            raise ValidationError({"task": "Log time only against an In progress task."})
        if task.assignee_id != self.employee_id:
            raise ValidationError({"employee": "Only the assigned employee can contribute time."})
        if (
            not User.objects.using(self._state.db)
            .filter(pk=self.employee_id, role=User.Role.EMPLOYEE, is_active=True)
            .exists()
        ):
            raise ValidationError({"employee": "Choose an active Employee."})
        if (
            not ProjectMembership.objects.using(self._state.db)
            .filter(project_id=task.project_id, employee_id=self.employee_id)
            .exists()
        ):
            raise ValidationError({"employee": "The employee must belong to the task's project."})

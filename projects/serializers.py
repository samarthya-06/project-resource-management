"""Transport parsing only; services/models validate business rules."""

from collections.abc import Mapping

from rest_framework import serializers

from projects.models import Project, ProjectMembership, Task, TimeEntry


class InputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {key: "Unknown or protected field." for key in unknown}
                )
        return super().to_internal_value(data)


class WholeIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if type(data) is not int:
            raise serializers.ValidationError(
                "Use a JSON whole integer, not a boolean, fraction or string."
            )
        return super().to_internal_value(data)


class ProjectInput(InputSerializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    manager_id = WholeIntegerField(required=False)
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class MembershipInput(InputSerializer):
    employee_id = WholeIntegerField()


class TaskInput(InputSerializer):
    project_id = WholeIntegerField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    assignee_id = WholeIntegerField()
    status = serializers.CharField(required=False)


class TaskCorrectionInput(InputSerializer):
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    assignee_id = WholeIntegerField(required=False)


class TimeInput(InputSerializer):
    task_id = WholeIntegerField()
    work_date = serializers.DateField()
    minutes = WholeIntegerField()
    note = serializers.CharField(required=False, allow_blank=True)


class TimeCorrectionInput(InputSerializer):
    work_date = serializers.DateField(required=False)
    minutes = WholeIntegerField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)


class ProjectOutput(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "manager_id", "start_date", "end_date"]
        read_only_fields = fields


class MembershipOutput(serializers.ModelSerializer):
    class Meta:
        model = ProjectMembership
        fields = ["id", "project_id", "employee_id"]
        read_only_fields = fields


class TaskOutput(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "project_id", "title", "description", "assignee_id", "status"]
        read_only_fields = fields


class TimeOutput(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = ["id", "task_id", "employee_id", "work_date", "minutes", "note"]
        read_only_fields = fields


class TaskFilters(serializers.Serializer):
    project = serializers.IntegerField(required=False, min_value=1)
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False)
    assignee = serializers.IntegerField(required=False, min_value=1)


class TimeFilters(serializers.Serializer):
    project = serializers.IntegerField(required=False, min_value=1)
    task = serializers.IntegerField(required=False, min_value=1)


def parsed(serializer_class, request, *, partial=False):
    serializer = serializer_class(data=request.data, partial=partial)
    serializer.is_valid(raise_exception=True)
    return dict(serializer.validated_data)

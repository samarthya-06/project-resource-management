from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import EmployeeOption
from projects import reports, selectors, services
from projects.serializers import (
    InputSerializer,
    MembershipInput,
    MembershipOutput,
    ProjectInput,
    ProjectOutput,
    TaskCorrectionInput,
    TaskFilters,
    TaskInput,
    TaskOutput,
    TimeCorrectionInput,
    TimeFilters,
    TimeInput,
    TimeOutput,
    parsed,
)


class ProjectViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ProjectOutput
    parser_classes = [JSONParser]

    def get_queryset(self):
        return selectors.projects_for(self.request.user).order_by("pk")

    def create(self, request):
        project = services.create_project(request.user, **parsed(ProjectInput, request))
        return Response(ProjectOutput(project).data, status=201)

    def update(self, request, pk=None):
        self.get_object()
        project = services.update_project(
            request.user, pk, **parsed(ProjectInput, request, partial=True)
        )
        return Response(ProjectOutput(project).data)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

    def destroy(self, request, pk=None):
        self.get_object()
        parsed(InputSerializer, request)
        services.delete_project(request.user, pk)
        return Response(status=204)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        return Response(reports.project_report(request.user, pk))


class MembershipViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = MembershipOutput
    parser_classes = [JSONParser]

    def get_queryset(self):
        project = selectors.project_for(self.request.user, self.kwargs["project_id"])
        return project.memberships.order_by("pk")

    def create(self, request, project_id=None):
        member = services.add_member(request.user, project_id, **parsed(MembershipInput, request))
        return Response(MembershipOutput(member).data, status=201)

    def destroy(self, request, project_id=None, employee_id=None):
        parsed(InputSerializer, request)
        services.remove_member(request.user, project_id, employee_id=employee_id)
        return Response(status=204)


class EmployeePicker(generics.ListAPIView):
    serializer_class = EmployeeOption

    def get_queryset(self):
        return selectors.membership_options_for(
            self.request.user, self.kwargs["project_id"]
        ).order_by("pk")


class TaskViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TaskOutput
    parser_classes = [JSONParser]

    def get_queryset(self):
        tasks = selectors.tasks_for(self.request.user)
        filters = TaskFilters(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        for param, field in [
            ("project", "project_id"),
            ("status", "status"),
            ("assignee", "assignee_id"),
        ]:
            if param in filters.validated_data:
                tasks = tasks.filter(**{field: filters.validated_data[param]})
        return tasks.order_by("pk")

    def create(self, request):
        data = parsed(TaskInput, request)
        project_id = data.pop("project_id")
        task = services.create_task(request.user, project_id, **data)
        return Response(TaskOutput(task).data, status=201)

    def update(self, request, pk=None):
        self.get_object()
        task = services.update_task(request.user, pk, **parsed(TaskInput, request, partial=True))
        return Response(TaskOutput(task).data)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

    def destroy(self, request, pk=None):
        self.get_object()
        parsed(InputSerializer, request)
        services.delete_task(request.user, pk)
        return Response(status=204)

    @action(detail=True, methods=["patch"], url_path="correction")
    def correction(self, request, pk=None):
        self.get_object()
        task = services.correct_completed_task(
            request.user, pk, **parsed(TaskCorrectionInput, request, partial=True)
        )
        return Response(TaskOutput(task).data)


class TimeEntryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TimeOutput
    parser_classes = [JSONParser]

    def get_queryset(self):
        entries = selectors.time_entries_for(self.request.user)
        filters = TimeFilters(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        for param, field in [("project", "task__project_id"), ("task", "task_id")]:
            if param in filters.validated_data:
                entries = entries.filter(**{field: filters.validated_data[param]})
        return entries.order_by("pk")

    def create(self, request):
        data = parsed(TimeInput, request)
        task_id = data.pop("task_id")
        entry = services.create_time_entry(request.user, task_id, **data)
        return Response(TimeOutput(entry).data, status=201)

    def update(self, request, pk=None):
        self.get_object()
        entry = services.update_time_entry(
            request.user, pk, **parsed(TimeInput, request, partial=True)
        )
        return Response(TimeOutput(entry).data)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

    def destroy(self, request, pk=None):
        self.get_object()
        parsed(InputSerializer, request)
        services.delete_time_entry(request.user, pk)
        return Response(status=204)

    @action(detail=True, methods=["patch"], url_path="correction")
    def correction(self, request, pk=None):
        self.get_object()
        entry = services.correct_time_entry(
            request.user, pk, **parsed(TimeCorrectionInput, request, partial=True)
        )
        return Response(TimeOutput(entry).data)


class Overview(APIView):
    def get(self, request):
        return Response(reports.overview_report(request.user))

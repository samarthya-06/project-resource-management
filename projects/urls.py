from django.urls import path

from projects import task_views, views

app_name = "projects"
urlpatterns = [
    path("my-tasks/", task_views.my_tasks, name="my_tasks"),
    path("projects/<int:project_id>/tasks/", task_views.project_tasks, name="tasks"),
    path("projects/<int:project_id>/tasks/create/", task_views.task_form, name="task_create"),
    path("tasks/<int:task_id>/", task_views.task_detail, name="task_detail"),
    path("tasks/<int:task_id>/edit/", task_views.task_form, name="task_edit"),
    path(
        "tasks/<int:task_id>/correction/",
        task_views.task_form,
        {"correction": True},
        name="task_correction",
    ),
    path("tasks/<int:task_id>/start/", task_views.task_start, name="task_start"),
    path("tasks/<int:task_id>/complete/", task_views.task_confirm, name="task_complete"),
    path(
        "tasks/<int:task_id>/delete/",
        task_views.task_confirm,
        {"deletion": True},
        name="task_delete",
    ),
    path("tasks/<int:task_id>/time/add/", task_views.time_form, name="time_add"),
    path("time-entries/<int:entry_id>/edit/", task_views.time_form, name="time_edit"),
    path(
        "time-entries/<int:entry_id>/correction/",
        task_views.time_form,
        {"correction": True},
        name="time_correction",
    ),
    path("time-entries/<int:entry_id>/delete/", task_views.time_delete, name="time_delete"),
    path("projects/", views.project_list, name="list"),
    path("projects/create/", views.project_form, name="create"),
    path("projects/<int:project_id>/", views.project_detail, name="detail"),
    path("projects/<int:project_id>/edit/", views.project_form, name="edit"),
    path("projects/<int:project_id>/team/", views.project_detail, {"section": "team"}, name="team"),
    path(
        "projects/<int:project_id>/report/",
        views.project_detail,
        {"section": "report"},
        name="report",
    ),
    path("projects/<int:project_id>/team/add/", views.member_add, name="member_add"),
    path(
        "projects/<int:project_id>/team/<int:employee_id>/remove/",
        views.member_remove,
        name="member_remove",
    ),
]

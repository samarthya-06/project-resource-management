"""Explicit development-only sample data, matching the Paper handoff totals."""

from datetime import date

from django.utils import timezone

from .models import Project, ProjectMembership, Task, TimeEntry


def seed_project_data(users, stdout):
    # Use a past/current work date even if a reviewer runs the demo before the
    # design's reference date. The illustrative project dates stay fixed.
    work_date = min(date(2026, 10, 6), timezone.localdate())
    specifications = [
        (
            "website-redesign",
            "Client Website Redesign",
            "neha@demo.local",
            date(2026, 10, 6),
            date(2026, 10, 23),
            "Refresh the website structure, content and navigation.",
            ["asha@demo.local", "ravi@demo.local"],
            [
                ("Design homepage layout", "asha@demo.local", Task.Status.IN_PROGRESS, 180),
                ("Implement navigation", "ravi@demo.local", Task.Status.IN_PROGRESS, 120),
                ("Review page content", "asha@demo.local", Task.Status.TODO, 0),
                ("Test mobile navigation", "ravi@demo.local", Task.Status.TODO, 0),
                ("Audit existing website", "asha@demo.local", Task.Status.COMPLETED, 240),
                ("Define content structure", "ravi@demo.local", Task.Status.COMPLETED, 180),
            ],
        ),
        (
            "onboarding-portal",
            "Employee Onboarding Portal",
            "neha@demo.local",
            date(2026, 10, 6),
            date(2026, 10, 30),
            "Create a clear welcome guide and checklist for new employees.",
            ["asha@demo.local", "ravi@demo.local"],
            [
                ("Build welcome checklist", "asha@demo.local", Task.Status.IN_PROGRESS, 120),
                ("Review welcome content", "asha@demo.local", Task.Status.TODO, 0),
                ("Prepare onboarding guide", "asha@demo.local", Task.Status.COMPLETED, 240),
                ("Review onboarding checklist", "ravi@demo.local", Task.Status.COMPLETED, 360),
                ("Test onboarding flow", "ravi@demo.local", Task.Status.TODO, 0),
            ],
        ),
        (
            "knowledge-base",
            "Internal Knowledge Base",
            "neha@demo.local",
            date(2026, 10, 7),
            date(2026, 10, 30),
            "A new project with no team, tasks or time yet.",
            [],
            [],
        ),
        (
            "operations-handbook",
            "Operations Handbook",
            "arjun@demo.local",
            date(2026, 10, 6),
            date(2026, 10, 23),
            "A separately owned project for manager data-isolation checks.",
            ["ravi@demo.local"],
            [("Draft operations outline", "ravi@demo.local", Task.Status.TODO, 0)],
        ),
    ]
    for key, name, manager, start, end, description, members, tasks in specifications:
        if Project.objects.filter(demo_key=key).exists():
            stdout.write(f"Preserved demo project {key} and all existing contents")
            continue
        project = Project.objects.create(
            demo_key=key,
            name=name,
            description=description,
            manager=users[manager],
            start_date=start,
            end_date=end,
        )
        for username in members:
            ProjectMembership.objects.create(project=project, employee=users[username])
        for title, username, status, minutes in tasks:
            task = Task.objects.create(project=project, title=title, assignee=users[username])
            if status != Task.Status.TODO:
                task.status = Task.Status.IN_PROGRESS
                task.save(update_fields=["status"])
            if minutes:
                TimeEntry.objects.create(
                    task=task,
                    employee=users[username],
                    work_date=work_date,
                    minutes=minutes,
                    note="Development demo work entry.",
                )
            if status == Task.Status.COMPLETED:
                task.status = status
                task.save(update_fields=["status"])
        stdout.write(f"Created demo project {name}")

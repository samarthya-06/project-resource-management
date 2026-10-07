"""Run read-only SQL and compare every project/contributor with Admin ORM reports.

Run from manage.py shell:
from scripts.verify_project_reports import verify
print(verify())
"""

from django.conf import settings
from django.db import connection, transaction

from accounts.models import User
from projects.reports import project_report


def verify():
    admin = (
        User.objects.filter(role=User.Role.ADMIN, is_active=True, must_change_password=False)
        .order_by("pk")
        .first()
    )
    if admin is None:
        raise RuntimeError("An active, password-ready Admin is required for comparison.")
    if connection.vendor != "postgresql":
        raise RuntimeError("Verification requires PostgreSQL.")
    sql = (settings.BASE_DIR / "sql/project_reports.sql").read_text()
    queries = [query.strip() for query in sql.split(";") if query.strip()]
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            results = []
            for query in queries:
                cursor.execute(query)
                columns = [column[0] for column in cursor.description]
                results.append([dict(zip(columns, row)) for row in cursor.fetchall()])
        projects, contributors = results
        reports = {row["project_id"]: project_report(admin, row["project_id"]) for row in projects}
        for row in projects:
            report = reports[row["project_id"]]
            for key in [
                "total_tasks",
                "completed_tasks",
                "completion_percentage",
                "total_minutes",
                "total_hours",
            ]:
                assert float(row[key]) == report[key], (
                    row["project_id"],
                    key,
                    row[key],
                    report[key],
                )
            assert (row["todo"], row["in_progress"]) == (
                report["task_counts"]["TODO"],
                report["task_counts"]["IN_PROGRESS"],
            )
        for project_id, report in reports.items():
            actual = {
                row["employee_id"]: (row["minutes"], float(row["hours"]))
                for row in contributors
                if row["project_id"] == project_id and row["employee_id"] is not None
            }
            expected = {
                row["employee_id"]: (row["minutes"], row["hours"]) for row in report["contributors"]
            }
            assert actual == expected, (project_id, actual, expected)
    return {
        "projects_compared": len(projects),
        "contributors_compared": sum(row["employee_id"] is not None for row in contributors),
        "totals": [
            {
                "project_id": row["project_id"],
                "tasks": row["total_tasks"],
                "completed": row["completed_tasks"],
                "minutes": row["total_minutes"],
            }
            for row in projects
        ],
        "result": "MATCH",
    }

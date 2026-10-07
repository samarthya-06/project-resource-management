-- Read-only assignment report queries. Full-database scope is for Admin/review.
-- Application reports scope project IDs via selectors before aggregation.
-- Managers: restrict projects to manager_id. Employees: membership projects,
-- tasks additionally to assignee_id, time additionally to original employee_id.
-- Do not expose these full-database queries as unscoped application endpoints.

-- Query 1: per-project task counts/completion and recorded time, including empty projects.
WITH task_totals AS (
    SELECT project_id, COUNT(*) AS total_tasks,
           COUNT(*) FILTER (WHERE status = 'TODO') AS todo,
           COUNT(*) FILTER (WHERE status = 'IN_PROGRESS') AS in_progress,
           COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed
    FROM projects_task
    GROUP BY project_id
), time_totals AS (
    SELECT t.project_id, SUM(e.minutes) AS minutes
    FROM projects_timeentry e JOIN projects_task t ON t.id = e.task_id
    GROUP BY t.project_id
)
SELECT p.id AS project_id, p.name,
       COALESCE(t.total_tasks, 0) AS total_tasks,
       COALESCE(t.todo, 0) AS todo,
       COALESCE(t.in_progress, 0) AS in_progress,
       COALESCE(t.completed, 0) AS completed_tasks,
       COALESCE(ROUND(100.0 * t.completed / NULLIF(t.total_tasks, 0), 2), 0) AS completion_percentage,
       COALESCE(w.minutes, 0) AS total_minutes,
       ROUND(COALESCE(w.minutes, 0) / 60.0, 2) AS total_hours
FROM projects_project p
LEFT JOIN task_totals t ON t.project_id = p.id
LEFT JOIN time_totals w ON w.project_id = p.id
ORDER BY p.id;

-- Query 2: hours by original contributor, never by current task assignee or membership.
-- Empty projects retain one row with NULL employee_id and zero time.
WITH contributions AS (
    SELECT t.project_id, e.employee_id, SUM(e.minutes) AS minutes
    FROM projects_timeentry e JOIN projects_task t ON t.id = e.task_id
    GROUP BY t.project_id, e.employee_id
)
SELECT p.id AS project_id, c.employee_id,
       COALESCE(c.minutes, 0) AS minutes,
       ROUND(COALESCE(c.minutes, 0) / 60.0, 2) AS hours
FROM projects_project p
LEFT JOIN contributions c ON c.project_id = p.id
ORDER BY p.id, c.employee_id;

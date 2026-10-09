# README setup verification

Executed 9 October 2026 against application commit `ea0366b`.

A clean local Git clone installed dependencies with the locked manifest, used a new
PostgreSQL database, applied migrations, seeded sample data and checked login/Overview.
The new database was removed afterward; development and hosted records were untouched.
This is an executed setup smoke check, not a human installer or full browser rehearsal.
PostgreSQL and uv were already installed; installer instructions and Windows were not executed.
The inherited `VIRTUAL_ENV` warning was harmless: uv ignored it and created the clone's own `.venv`.
The original checkout path is redacted in captured warnings.

## `uv python install 3.12`

Exit code: 0.

```text
Python 3.12 is already installed
```

## `uv sync --locked`

Exit code: 0.

```text
warning: `VIRTUAL_ENV=[original working copy]/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
Using CPython 3.12.15
Creating virtual environment at: .venv
Resolved 32 packages in 5ms
Installed 29 packages in 245ms
 + asgiref==3.12.1
 + certifi==2026.7.22
 + charset-normalizer==3.5.2
 + django==5.2.18
 + django-environ==0.14.0
 + djangorestframework==3.18.3
 + greenlet==3.5.6
 + gunicorn==26.2.0
 + idna==3.20
 + iniconfig==2.3.1
 + packaging==26.3
 + playwright==1.63.0
 + pluggy==1.6.0
 + psycopg==3.3.6
 + psycopg-binary==3.3.6
 + pyee==13.0.1
 + pygments==2.21.0
 + pytest==9.1.1
 + pytest-base-url==2.1.0
 + pytest-django==4.14.0
 + pytest-playwright==0.9.0
 + python-slugify==8.0.4
 + requests==2.34.2
 + ruff==0.16.10
 + sqlparse==0.6.0
 + text-unidecode==1.3
 + typing-extensions==4.16.0
 + urllib3==2.8.0
 + whitenoise==6.12.0
```

## `uv run python manage.py migrate`

Exit code: 0.

```text
Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, projects, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0001_initial... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying accounts.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying admin.0003_logentry_add_action_flag_choices... OK
  Applying projects.0001_initial... OK
  Applying sessions.0001_initial... OK
warning: `VIRTUAL_ENV=[original working copy]/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

## `uv run python manage.py seed_demo`

Exit code: 0.

```text
Created admin@demo.local (Admin)
Created neha@demo.local (Project Manager)
Created arjun@demo.local (Project Manager)
Created asha@demo.local (Employee)
Created ravi@demo.local (Employee)
Created meera@demo.local (Employee)
Created dev@demo.local (Employee)
Created demo project Client Website Redesign
Created demo project Employee Onboarding Portal
Created demo project Internal Knowledge Base
Created demo project Operations Handbook
Demo data ready. Account password is DEMO_PASSWORD; never printed.
warning: `VIRTUAL_ENV=[original working copy]/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

## `uv run python manage.py check`

Exit code: 0.

```text
System check identified no issues (0 silenced).
warning: `VIRTUAL_ENV=[original working copy]/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

## `uv run python manage.py makemigrations --check --dry-run`

Exit code: 0.

```text
No changes detected
warning: `VIRTUAL_ENV=[original working copy]/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

## `uv run python manage.py dbshell`

Exit code: 0.

```text
users
-------
     7
(1 row)

 projects
----------
        4
(1 row)

 tasks
-------
    12
(1 row)

 entries
---------
       7
(1 row)

warning: `VIRTUAL_ENV=[original working copy]/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

## SQL comparison

Invocation: `uv run python manage.py shell -c "from scripts.verify_project_reports import verify; print(verify())"`.

Exit code: 0.

```text
10 objects imported automatically (use -v 2 for details).

{'projects_compared': 4, 'contributors_compared': 4, 'totals': [{'project_id': 1, 'tasks': 6, 'completed': 2, 'minutes': 720}, {'project_id': 2, 'tasks': 5, 'completed': 2, 'minutes': 720}, {'project_id': 3, 'tasks': 0, 'completed': 0, 'minutes': 0}, {'project_id': 4, 'tasks': 1, 'completed': 0, 'minutes': 0}], 'result': 'MATCH'}
warning: `VIRTUAL_ENV=[original working copy]/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

## Admin login and Overview smoke check

Executed a Django test-client login with the fresh sample Admin and generated password.
Checked redirect status 302 and Overview status 200. This subcheck does not exercise browser CSRF.

Exit code: 0.

```text
10 objects imported automatically (use -v 2 for details).

Fresh sample Admin login and Overview: PASS
warning: `VIRTUAL_ENV=[original working copy]/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

import json
import os
import subprocess
import sys

from django.test import Client, override_settings


def settings_process(database_url):
    environment = os.environ.copy()
    environment.update(
        DJANGO_SECRET_KEY="deployment-test-secret-with-more-than-fifty-characters-482!",
        DJANGO_DEBUG="False",
        DATABASE_URL=database_url,
        RENDER_EXTERNAL_HOSTNAME="assignment-test.onrender.com",
        DJANGO_ALLOWED_HOSTS="localhost",
        DJANGO_SECURE_SSL_REDIRECT="True",
    )
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from config import settings as s; "
            "print(json.dumps([s.DEBUG, s.ALLOWED_HOSTS, s.CSRF_TRUSTED_ORIGINS, "
            "s.SECURE_PROXY_SSL_HEADER, s.DATABASES['default']['ENGINE'], "
            "s.DATABASES['default']['OPTIONS'], "
            "s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE]))",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_render_settings_accept_postgresql_tls_url_and_scope_host():
    result = settings_process("postgresql://test:unused@localhost/test?sslmode=require")
    assert result.returncode == 0, result.stderr
    debug, hosts, origins, proxy, engine, options, session_secure, csrf_secure = json.loads(
        result.stdout
    )
    assert debug is False
    assert hosts == ["localhost", "assignment-test.onrender.com"]
    assert origins == ["https://assignment-test.onrender.com"]
    assert proxy == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert engine == "django.db.backends.postgresql"
    assert options["sslmode"] == "require"
    assert session_secure is True
    assert csrf_secure is True


def test_deployment_rejects_non_postgresql_database():
    result = settings_process("sqlite:///unused.sqlite3")
    assert result.returncode != 0
    assert "DATABASE_URL must use PostgreSQL" in result.stderr


@override_settings(
    DEBUG=False,
    SECURE_SSL_REDIRECT=True,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    CSRF_COOKIE_SECURE=True,
)
def test_https_proxy_serves_login_without_redirect_loop():
    client = Client()
    assert client.get("/login/").status_code == 301
    response = client.get("/login/", HTTP_X_FORWARDED_PROTO="https")
    assert response.status_code == 200
    assert response.cookies["csrftoken"]["secure"]


@override_settings(DEBUG=False)
def test_collected_css_is_served_without_login():
    # collectstatic is part of the documented verification/build sequence.
    response = Client().get("/static/css/workspace.css", secure=True)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/css")

"""Desktop authentication smoke check against an explicitly seeded local app."""

import os
from pathlib import Path

import environ
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(ROOT / ".env", overwrite=False)
base_url = os.environ.get("AUTH_BASE_URL", "http://127.0.0.1:8000")
password = env("DEMO_PASSWORD")
evidence = ROOT / "docs" / "evidence" / "authentication"
evidence.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(base_url + "/login/")
    page.get_by_role("heading", name="Sign in").wait_for()
    page.evaluate("document.fonts.ready")
    assert (
        page.locator("body")
        .evaluate("el => getComputedStyle(el).fontFamily")
        .startswith('"IBM Plex Sans"')
    )
    assert page.locator(".auth-card").bounding_box()["width"] == 440
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "login.png"))
    page.get_by_label("Login identifier").fill("asha@demo.local")
    page.get_by_label("Password", exact=True).fill("incorrect-password")
    page.get_by_role("button", name="Show", exact=True).click()
    assert page.get_by_label("Password", exact=True).get_attribute("type") == "text"
    page.get_by_role("button", name="Hide", exact=True).click()
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_role("alert").wait_for()
    assert (
        "The login identifier or password is incorrect." in page.get_by_role("alert").inner_text()
    )
    assert page.get_by_label("Login identifier").input_value() == "asha@demo.local"
    assert page.get_by_label("Password", exact=True).input_value() == ""
    page.screenshot(path=str(evidence / "login-error.png"))
    print("PASS: desktop login layout, local font, Show/Hide and failed-login state")

    for username, role in [
        ("admin@demo.local", "ADMIN"),
        ("neha@demo.local", "PROJECT_MANAGER"),
        ("asha@demo.local", "EMPLOYEE"),
    ]:
        page.goto(base_url + "/login/")
        page.get_by_label("Login identifier").fill(username)
        page.get_by_label("Password", exact=True).fill(password)
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.wait_for_url(base_url + "/")
        response = context.request.get(base_url + "/api/auth/me/")
        assert response.status == 200 and response.json()["role"] == role
        assert response.json()["username"] == username
        page.get_by_role("link", name="Change password", exact=True).click()
        page.get_by_role("heading", name="Change password", exact=True).wait_for()
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.wait_for_url(base_url + "/login/")
        assert context.request.get(base_url + "/api/auth/me/").status == 403
        print("PASS: login, identity, password page and POST sign-out for", role)

    page.get_by_label("Login identifier").fill("meera@demo.local")
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_role("alert").wait_for()
    assert context.request.get(base_url + "/api/auth/me/").status == 403
    print("PASS: inactive demo account rejected")
    context.close()
    browser.close()

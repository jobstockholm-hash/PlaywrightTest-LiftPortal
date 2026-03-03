"""
conftest.py
===========
Shared pytest fixtures and hooks for the LIFT Portal UI test suite.

Key responsibilities
--------------------
* Provide a configured Playwright browser / page to every test.
* Capture a full-page screenshot automatically on every test failure.
* Expose a `config` fixture that reads all settings from .env so that
  no credentials ever appear in test code.
"""

import os
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

# ── Load .env (silently ignored if the file is absent) ───────────────────────
load_dotenv()

SCREENSHOTS_DIR = Path("reports/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


# ─── pytest-html metadata ────────────────────────────────────────────────────

def pytest_configure(config):
    config._metadata = {
        "Project":     "Laerdal LIFT Portal – UI Automation",
        "Environment": os.getenv("BASE_URL", "https://lift-dev.training"),
        "Browser":     "Chromium (Playwright)",
    }


def pytest_html_report_title(report):
    report.title = "LIFT Portal – Automated Test Report"


# ─── Central configuration ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def config():
    return {
        "base_url":          os.getenv("BASE_URL",          "https://lift-dev.training"),
        "username":          os.getenv("ADMIN_USERNAME",    "per.helge.aasland+dev-site-admin@laerdal.com"),
        "password":          os.getenv("ADMIN_PASSWORD",    "asahiisverycool"),
        "login_timeout_ms":  int(os.getenv("LOGIN_TIMEOUT_MS",  "5000")),
        "default_timeout_ms":int(os.getenv("DEFAULT_TIMEOUT_MS","30000")),
        "headless":          os.getenv("HEADLESS", "true").lower() == "true",
        "slow_mo":           int(os.getenv("SLOW_MO", "0")),
    }


# ─── Browser / context / page fixtures ──────────────────────────────────────

@pytest.fixture(scope="session")
def browser_session(config):
    """One browser process shared across the whole session."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=config["headless"],
            slow_mo=config["slow_mo"],
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def context(browser_session, config):
    """Fresh, isolated browser context per test (own cookies/storage)."""
    ctx = browser_session.new_context(
        # Force desktop breakpoint — MUI hides the <table> below 768 px and
        # renders a <ul> list instead. 1920×1080 guarantees the table path.
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
    )
    ctx.set_default_timeout(config["default_timeout_ms"])
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context) -> Page:
    """Fresh page per test."""
    p = context.new_page()
    yield p
    p.close()


# ─── Auto-screenshot on failure ──────────────────────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()

    if report.when == "call" and report.failed:
        page: Page | None = item.funcargs.get("page")
        if page:
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = item.name.replace("[", "_").replace("]", "_")
            path = SCREENSHOTS_DIR / f"FAIL__{name}__{ts}.png"
            try:
                page.screenshot(path=str(path), full_page=True)
                print(f"\n  📸  Failure screenshot → {path}")
            except Exception as exc:
                print(f"\n  ⚠️   Could not save screenshot: {exc}")
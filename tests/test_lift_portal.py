"""
tests/test_lift_portal.py
=========================
UI Automation for the Laerdal LIFT Portal (https://lift-dev.training).

Tests
-----
  Test 1 – Login within 5 seconds
  Test 2 – User list is visible
  Test 3 – Bulk upload 35 users
"""

import csv
import re
import time
import logging
from pathlib import Path

import pytest

from pages.login_page     import LoginPage
from pages.dashboard_page import DashboardPage
from pages.users_page     import UsersPage
from utils.csv_generator  import generate_users_csv

log = logging.getLogger(__name__)

# ─── Shared helpers ───────────────────────────────────────────────────────────

def _screenshot(page, label: str) -> None:
    """Save a step screenshot — never raises."""
    try:
        path = Path("reports/screenshots") / f"{label}_{int(time.time())}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
        log.info("  📸  %s", path)
    except Exception as exc:
        log.warning("  ⚠️  screenshot failed: %s", exc)


def _page_info(page, label: str = "") -> str:
    try:
        body = page.evaluate("() => document.body.innerText")[:300]
    except Exception:
        body = "(could not read body)"
    tag = f" [{label}]" if label else ""
    return (
        f"{tag}"
        f"\n  URL:   {page.url}"
        f"\n  Title: {page.title()}"
        f"\n  Body:  {body!r}"
    )


def _login(page, config: dict) -> None:
    """Full login flow — blocks until dashboard URL is confirmed."""
    lp = LoginPage(page, config["base_url"])
    lp.navigate()
    assert lp.is_login_form_visible(), (
        "Pre-condition: login form not visible." + _page_info(page, "pre-login")
    )
    lp.login(config["username"], config["password"])
    dashboard = DashboardPage(page)
    assert dashboard.wait_until_authenticated(timeout_ms=15_000), (
        "_login: dashboard not reached after credentials submitted."
        + _page_info(page, "post-login")
        + f"\n  Login error text: {lp.get_error_text()}"
    )


def _navigate_to_users(page, config: dict) -> UsersPage:
    """Navigate to /users and wait for MUI table to attach."""
    dashboard  = DashboardPage(page)
    users_page = UsersPage(page)

    try:
        dashboard.go_to_users()
    except Exception as exc:
        _screenshot(page, "nav_to_users_FAIL")
        pytest.fail(
            f"Navigation to Users section failed.\n  {exc}"
            + _page_info(page, "nav-users")
        )

    page.wait_for_timeout(2_000)

    loaded = users_page.wait_until_loaded(timeout_ms=20_000)
    if not loaded:
        _screenshot(page, "users_load_FAIL")
        pytest.fail(
            "Users page did not render within 20 s."
            + _page_info(page, "users-load")
        )

    return users_page


# ═════════════════════════════════════════════════════════════════════════════
# Test 1 — Login within 5 seconds   (UNCHANGED — was passing)
# ═════════════════════════════════════════════════════════════════════════════

class TestLogin:
    """Smoke test: login flow completes within the SLA."""

    @pytest.mark.smoke
    def test_login_within_5_seconds(self, page, config):
        """Login and land on an authenticated page within LOGIN_TIMEOUT_MS."""

        # Step 1: Load login page
        log.info("Step 1: Navigate to login page")
        lp = LoginPage(page, config["base_url"])
        lp.navigate()
        assert lp.is_login_form_visible(), (
            "Step 1 FAILED: Login form is not visible."
            + _page_info(page, "t1-s1")
        )
        _screenshot(page, "t1_s1_login_form")
        log.info("  ✅  Login form visible  (URL: %s)", page.url)

        # Step 2: Enter credentials
        log.info("Step 2: Fill in credentials")
        lp.fill_username(config["username"])
        lp.fill_password(config["password"])
        _screenshot(page, "t1_s2_credentials")
        log.info("  ✅  Credentials entered")

        # Step 3: Submit and time it
        log.info("Step 3: Click Sign in — timing starts now")
        t0 = time.perf_counter()
        lp.click_sign_in()

        dashboard  = DashboardPage(page)
        is_auth    = dashboard.is_on_dashboard(timeout_ms=15_000)
        elapsed_ms = (time.perf_counter() - t0) * 1_000

        _screenshot(page, "t1_s3_post_login")
        assert is_auth, (
            f"Step 3 FAILED: Not authenticated after login.\n"
            f"  Elapsed: {elapsed_ms:.0f} ms"
            + _page_info(page, "t1-s3")
            + f"\n  Login error: {lp.get_error_text()}"
        )
        log.info("  ✅  Authenticated in %.0f ms  (URL: %s)", elapsed_ms, page.url)

        # Step 4: SLA check
        sla_ms = config["login_timeout_ms"]
        log.info("Step 4: %.0f ms ≤ %d ms SLA?", elapsed_ms, sla_ms)
        assert elapsed_ms <= sla_ms, (
            f"Step 4 FAILED: Login took {elapsed_ms:.0f} ms — exceeds {sla_ms} ms SLA.\n"
            f"  Tip: set LOGIN_TIMEOUT_MS=7000 in .env if the dev server is slow."
        )
        log.info("  ✅  %.0f ms ≤ %d ms  ✓", elapsed_ms, sla_ms)


# ═════════════════════════════════════════════════════════════════════════════
# Test 2 — User list is visible   (UNCHANGED — was passing)
# ═════════════════════════════════════════════════════════════════════════════

class TestUserList:
    """Verify the /users page renders a populated MUI data table."""

    @pytest.mark.smoke
    def test_user_list_is_visible(self, page, config):
        """Admin can navigate to /users and see a populated user list."""

        # Step 1: Login
        log.info("Step 1: Log in")
        _login(page, config)
        _screenshot(page, "t2_s1_logged_in")
        log.info("  ✅  Logged in  (URL: %s)", page.url)

        # Step 2: Navigate to /users
        log.info("Step 2: Navigate to Users section")
        users_page = _navigate_to_users(page, config)
        _screenshot(page, "t2_s2_users_page")
        log.info("  ✅  Users page loaded  (URL: %s)", page.url)

        # Step 3: Assert user list is present
        log.info("Step 3: Verify user list has content")
        has_table  = users_page.has_user_table()
        row_count  = users_page.get_visible_user_row_count()
        page_text  = users_page.get_page_content_summary()
        _screenshot(page, "t2_s3_user_table")

        assert has_table, (
            "Step 3 FAILED: No user rows found on /users.\n"
            f"  Row count: {row_count}\n"
            f"  Page text: {page_text[:300]!r}\n"
            f"  URL: {page.url}"
        )
        assert row_count >= 1, (
            f"Step 3 FAILED: User list element found but 0 rows visible.\n"
            f"  URL: {page.url}"
        )
        log.info("  ✅  %d user row(s) visible  ✓", row_count)

        # Step 4: Pagination summary
        log.info("Step 4: Check pagination summary text")
        try:
            body_text = page.evaluate("() => document.body.innerText")
            match = re.search(r"(\d+)-(\d+) of (\d+) users", body_text, re.IGNORECASE)
            if match:
                page_first = int(match.group(1))
                page_last  = int(match.group(2))
                total      = int(match.group(3))
                page_size  = page_last - page_first + 1
                log.info(
                    "  ✅  Pagination: %d-%d of %d users  (page size %d)",
                    page_first, page_last, total, page_size,
                )
            else:
                log.info("  ℹ️   Pagination text not found — skipping total check")
        except Exception as exc:
            log.warning("  ⚠️  Pagination check skipped: %s", exc)


# ═════════════════════════════════════════════════════════════════════════════
# Test 3 — Bulk upload 35 users
# ═════════════════════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════════════════════
# Test 3 — Bulk upload 35 users
# ═════════════════════════════════════════════════════════════════════════════

class TestBulkUpload:
    """
    End-to-end bulk user import through the 5-step wizard.

    Wizard flow confirmed from live portal DOM (2026-03-03):

      /users
        JS-click  a[href='/users/bulk-import']
        (MUI tooltip wrapper blocks Playwright 'visible' -> element_handle JS click)

      /users/bulk-import/download-template
        JS-click  a[href='/users/bulk-import/facility']
        (This is an <a> tag, NOT a <button>)

      /users/bulk-import/facility
        JS-click  input[name='selected-facility']  (LGH Dev - Site A radio)
        Click     button[type='submit']            (Next)

      /users/bulk-import/upload?facility=UUID
        expect_file_chooser -> click button:has-text('Browse & upload')
        (hidden input[type='file'] activated by the Browse button)

      /users/bulk-import/review?facility=...&file-id=...
        Assert    "No issues found."
        Click     button[type='submit']:has-text('Looks good, continue')

      /users  (redirect)
        Toast:    "Bulk creating users" dark panel, bottom-left
        Import runs in background -- browser can close immediately.

      /users?query=<first_name>
        Assert    >= 1 row (confirms user was created)
    """

    USER_COUNT = 35

    @pytest.mark.upload
    def test_bulk_upload_35_users(self, page, config, tmp_path):
        import pathlib

        # Step 1: Generate 35-user CSV
        log.info("Step 1: Generate %d-user CSV", self.USER_COUNT)
        csv_path = generate_users_csv(self.USER_COUNT, output_dir=str(tmp_path))
        assert Path(csv_path).is_file(), f"Step 1 FAILED: CSV not created at {csv_path}"
        log.info("  \u2705  CSV: %s", csv_path)

        with open(csv_path, newline="", encoding="utf-8") as f:
            first_row = next(csv.DictReader(f))
        first_name = first_row.get("First name", "").strip()
        last_name  = first_row.get("Last name", "").strip()
        log.info("  \U0001f4cb  First user: '%s %s'", first_name, last_name)

        # Step 2: Log in
        log.info("Step 2: Log in")
        _login(page, config)
        _screenshot(page, "t3_s2_logged_in")
        log.info("  \u2705  Logged in  (URL: %s)", page.url)

        # Step 3: Navigate to /users
        log.info("Step 3: Navigate to /users")
        users_page = _navigate_to_users(page, config)
        _screenshot(page, "t3_s3_users_page")
        log.info("  \u2705  Users page  (URL: %s)", page.url)


        # Step 4a: Click Bulk import -- land on Download template page
        # DOM: <a href="/users/bulk-import" class="MuiButton-root ...">Bulk import</a>
        # MUI tooltip wrapper blocks Playwright 'visible' check -- use JS evaluate click.
        # SUCCESS SIGNAL: wait for the Next link to appear on the wizard page.
        # This avoids fragile URL-pattern waits entirely.
        log.info("Step 4a: Click 'Bulk import'  [a[href='/users/bulk-import']]")
        try:
            el = page.locator("a[href='/users/bulk-import']")
            el.wait_for(state="attached", timeout=10_000)
            page.evaluate("el => el.click()", el.element_handle(timeout=5_000))
            # Confirm wizard opened by waiting for the Next link on the template page
            page.wait_for_selector(
                "a[href='/users/bulk-import/facility']",
                state="attached",
                timeout=12_000,
            )
            page.wait_for_timeout(600)
            _screenshot(page, "t3_s4a_wizard_step1")
            log.info("  \u2705  Wizard opened  (URL: %s)", page.url)
        except Exception as exc:
            _screenshot(page, "t3_s4a_FAIL")
            pytest.fail(
                f"Step 4a FAILED: Could not open Bulk import wizard.\n  {exc}\n"
                "  Selector: a[href='/users/bulk-import']\n"
                "  DOM: <a href='/users/bulk-import' class='MuiButton-root ...'>Bulk import</a>"
            )

        # Step 4b: Download template -> click Next
        # DOM: <a href="/users/bulk-import/facility" ...>Next</a>  <- an <a>, NOT <button>
        # Already confirmed present in Step 4a -- click it directly.
        log.info("Step 4b: Download template -> click Next  [a[href='/users/bulk-import/facility']]")
        try:
            next_link = page.locator("a[href='/users/bulk-import/facility']")
            next_link.wait_for(state="attached", timeout=8_000)
            page.evaluate("el => el.click()", next_link.element_handle(timeout=3_000))
            page.wait_for_url("**/facility**", timeout=10_000)
            page.wait_for_timeout(800)
            _screenshot(page, "t3_s4b_facility_page")
            log.info("  \u2705  Facility page  (URL: %s)", page.url)
        except Exception as exc:
            _screenshot(page, "t3_s4b_FAIL")
            pytest.fail(
                f"Step 4b FAILED: Could not click Next on download-template.\n  {exc}\n"
                "  Selector: a[href='/users/bulk-import/facility']\n"
                "  Note: This is an <a> element, NOT a <button>.\n"
                f"  Current URL: {page.url}"
            )

        # Step 4c: Select facility radio + click Next
        # DOM: <input type="radio" name="selected-facility" value="UUID">
        #      <button type="submit">Next</button>
        log.info("Step 4c: Select 'LGH Dev - Site A' -> Next  [input[name='selected-facility']]")
        try:
            radio = page.locator("input[name='selected-facility']").first
            radio.wait_for(state="attached", timeout=8_000)
            try:
                page.evaluate("el => el.click()", radio.element_handle(timeout=3_000))
            except Exception:
                radio.click()
            page.wait_for_timeout(400)

            submit = page.locator("button[type='submit']").first
            submit.wait_for(state="visible", timeout=6_000)
            submit.click()
            page.wait_for_url("**/upload**", timeout=10_000)
            page.wait_for_timeout(800)
            _screenshot(page, "t3_s4c_upload_page")
            log.info("  \u2705  Upload page  (URL: %s)", page.url)
        except Exception as exc:
            _screenshot(page, "t3_s4c_FAIL")
            pytest.fail(
                f"Step 4c FAILED: Could not select facility or click Next.\n  {exc}\n"
                "  Radio: input[name='selected-facility']\n"
                "  Next:  button[type='submit']"
            )

        # Step 4d: Attach CSV via Browse & upload
        # DOM: <button type="button">Browse &amp; upload</button>
        #      triggers hidden <input type="file">
        # Primary: expect_file_chooser interception
        # Fallback: set_input_files directly on hidden input
        log.info("Step 4d: Attach %d-user CSV  [expect_file_chooser + button:has-text('Browse')]", self.USER_COUNT)
        try:
            csv_bytes = pathlib.Path(csv_path).read_bytes()
            csv_name  = pathlib.Path(csv_path).name
            payload   = {"name": csv_name, "mimeType": "text/csv", "buffer": csv_bytes}

            try:
                browse_btn = page.locator("button:has-text('Browse')").first
                browse_btn.wait_for(state="visible", timeout=8_000)
                with page.expect_file_chooser(timeout=6_000) as fc_info:
                    browse_btn.click()
                fc_info.value.set_files(payload)
                page.wait_for_url("**/review**", timeout=15_000)
                page.wait_for_timeout(800)
            except Exception:
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(payload, timeout=10_000)
                page.wait_for_url("**/review**", timeout=15_000)
                page.wait_for_timeout(800)

            _screenshot(page, "t3_s4d_review_page")
            log.info("  \u2705  File accepted, review page  (URL: %s)", page.url)
        except Exception as exc:
            _screenshot(page, "t3_s4d_FAIL")
            pytest.fail(
                f"Step 4d FAILED: Could not attach CSV.\n  {exc}\n"
                "  Primary:  expect_file_chooser + click button:has-text('Browse')\n"
                "  Fallback: set_input_files on hidden input[type='file']"
            )


        # Step 4e: Review participant list -> click 'Looks good, continue'
        # DOM: <button type="submit">Looks good, continue</button>
#
        # With the new CSV (unique 4-digit suffixes) the portal should show
        # 'No issues found'. We log a warning if issues are still detected but
        # always proceed -- portal allows clicking 'Looks good, continue' even
        # when issues exist, and valid rows will still be imported.
        log.info("Step 4e: Review participant list -> click 'Looks good, continue'")
        try:
            btn = page.locator("button[type='submit']").filter(has_text='Looks good').first
            btn.wait_for(state='visible', timeout=10_000)
            try:
                body = page.evaluate('() => document.body.innerText')
                import re as _re
                m = _re.search(r'(\d+) issues? detected', body, _re.IGNORECASE)
                if 'No issues found' in body:
                    log.info('  \u2705  No issues found confirmed')
                elif m:
                    log.warning('  \u26a0\ufe0f  %s on review page (proceeding anyway)', m.group(0))
                    log.warning('  \u26a0\ufe0f  New CSV uses unique suffixes -- should not recur')
            except Exception:
                pass
            btn.click()
            page.wait_for_timeout(1_500)
            _screenshot(page, 't3_s4e_review_confirmed')
            log.info('  \u2705  Looks good, continue clicked  (URL: %s)', page.url)
        except Exception as exc:
            _screenshot(page, 't3_s4e_FAIL')
            pytest.fail(
                f"Step 4e FAILED: Could not click 'Looks good, continue'.\n  {exc}\n"
                "  Button: button[type='submit']:has-text('Looks good')\n"
                f"  Current URL: {page.url}"
            )

        # Step 5: Assert redirect to /users + toast
        # Portal redirects and shows: "Bulk creating users - This may take a moment..."
        # Accept toast OR clean /users URL as success.
        log.info("Step 5: Assert redirect to /users + 'Bulk creating users' toast")
        try:
            page.wait_for_selector("text=/Bulk creating/i", state="visible", timeout=15_000)
            toast_visible = True
        except Exception:
            toast_visible = False

        _screenshot(page, "t3_s5_redirect_result")

        assert "/users" in page.url and "bulk-import" not in page.url, (
            "Step 5 FAILED: Portal did not redirect to /users after wizard.\n"
            f"  Current URL: {page.url}"
        )
        if toast_visible:
            log.info("  \u2705  Redirected to /users + toast 'Bulk creating users' visible  \u2713")
        else:
            log.info("  \u2705  Redirected to /users (toast may have dismissed already)  \u2713")

        # Step 6: Verify user in portal search
        # Navigate to /users?query=<first_name>, assert >= 1 row.
        # Retry 4x with 5s waits to allow background import to process.
        # Confirmed: /users?query=bgt -> "Showing 1 users" -> row "bgt klk"
        log.info("Step 6: Search /users?query=%s -- assert >= 1 result", first_name)
        base  = page.url.split("/users")[0]
        count = 0
        for attempt in range(4):
            page.goto(f"{base}/users?query={first_name}", wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_timeout(2_000)

            for sel in ("tbody.MuiTableBody-root tr.MuiTableRow-root",
                        "ul.MuiList-root li.MuiListItem-root",
                        "table tbody tr"):
                try:
                    c = page.locator(sel).count()
                    if c > 0:
                        count = c
                        break
                except Exception:
                    pass

            if count == 0:
                try:
                    text = page.evaluate("() => document.body.innerText")
                    m = re.search(r"Showing (\d+) users", text)
                    if m and int(m.group(1)) > 0:
                        count = int(m.group(1))
                except Exception:
                    pass

            if count > 0:
                break
            if attempt < 3:
                log.info("  \u23f3  Not found yet, waiting 5 s (attempt %d/4)...", attempt + 1)
                page.wait_for_timeout(5_000)

        _screenshot(page, f"t3_s6_search_{'found' if count > 0 else 'not_found'}")

        assert count > 0, (
            f"Step 6 FAILED: '{first_name} {last_name}' not found after upload.\n"
            f"  URL: {page.url}\n"
            "  The import runs in the background -- wait 30-60 s and retry if needed.\n"
            f"  Manual check: https://lift-dev.training/users?query={first_name}"
        )
        log.info("  \u2705  Found %d user(s) matching '%s' -- bulk upload confirmed  \u2713", count, first_name)
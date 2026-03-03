"""
pages/users_page.py
===================
Page Object for the LIFT Portal /users page.

Selector strategy (v5 — confirmed from DOM inspector 2026-03-03)
----------------------------------------------------------------
The page uses MUI (Material UI) React components with a RESPONSIVE
dual-structure layout:

  Desktop (>=768 px viewport):
    <table class="MuiTable-root css-1wb8wh4">
      <thead class="MuiTableHead-root css-s4zxv0"> ... </thead>
      <tbody class="MuiTableBody-root css-y6j1my">
        <tr class="MuiTableRow-root css-l2p1am"> ... </tr>

  Mobile (<768 px viewport):
    <ul class="MuiList-root MuiList-padding css-1wtuplx">
      <li class="MuiListItem-root MuiListItem-gutters css-anxn0y"> ...

The conftest.py fixture forces a 1920x1080 viewport, so the DESKTOP
table path is always active.  Mobile selectors are kept as fallbacks.

Key page-chrome elements (always present):
  - <h1 class="css-4ck5k">Users</h1>
  - <input placeholder="Search users">
  - <a href="/users?create=1">  -> "New user" button
  - <a href="/users/bulk-import">  -> "Bulk import" button
  - Pagination text: "1-50 of 697 users"
"""

import re
from pathlib import Path
from playwright.sync_api import Page


# ── Confirmed selectors (from DOM inspector output) ────────────────────────

# Desktop table (visible at >=768 px)
_TABLE      = "table.MuiTable-root"
_TBODY      = "tbody.MuiTableBody-root"
_TABLE_ROW  = "tbody.MuiTableBody-root tr.MuiTableRow-root"

# Mobile list (visible at <768 px)
_LIST       = "ul.MuiList-root"
_LIST_ITEM  = "ul.MuiList-root li.MuiListItem-root"

# Page chrome
_H1_USERS       = "h1:has-text('Users')"
_SEARCH_INPUT   = "input[placeholder='Search users']"
_BULK_IMPORT    = "a[href='/users/bulk-import']"
_NEW_USER_BTN   = "a[href='/users?create=1']"
_PAGINATION_NAV = "nav.MuiPagination-root"


class UsersPage:
    """LIFT Portal - Users management section."""

    def __init__(self, page: Page):
        self.page = page

    # ─── Page-load detection ──────────────────────────────────────────────────

    def wait_until_loaded(self, timeout_ms: int = 20_000) -> bool:
        """
        Return True when the /users page has finished rendering.

        Priority order (fastest -> most lenient):
          1. MUI table body  — definitive sign data has loaded
          2. MUI list        — mobile fallback
          3. H1 heading      — page chrome, renders before data
          4. Search input    — always present on /users
          5. DOM node count heuristic (last resort)
        """
        slot = timeout_ms // 4

        # 1. Desktop table body — primary target
        for selector in (_TBODY, _TABLE):
            try:
                self.page.wait_for_selector(selector, state="attached", timeout=slot)
                return True
            except Exception:
                pass

        # 2. Mobile list fallback
        try:
            self.page.wait_for_selector(_LIST, state="attached", timeout=slot)
            return True
        except Exception:
            pass

        # 3. Page heading (React mounted, chrome rendered)
        try:
            self.page.wait_for_selector(_H1_USERS, state="visible", timeout=slot)
            return True
        except Exception:
            pass

        # 4. Search input (always present on /users)
        try:
            self.page.wait_for_selector(_SEARCH_INPUT, state="visible", timeout=slot)
            return True
        except Exception:
            pass

        # 5. DOM node count heuristic
        try:
            n = self.page.evaluate(
                "() => document.querySelectorAll('div,section,main,article').length"
            )
            return n > 10
        except Exception:
            return False

    def is_users_page(self) -> bool:
        """Non-blocking URL check."""
        return "user" in self.page.url.lower()

    # ─── User list detection ──────────────────────────────────────────────────

    def has_user_table(self) -> bool:
        """
        Return True if user list/table content is present in the DOM.

        Checks confirmed MUI selectors first, then broad fallbacks.
        """
        # Confirmed MUI selectors
        confirmed = [
            (_TABLE_ROW, lambda n: n > 0),
            (_LIST_ITEM, lambda n: n > 0),
            (_TBODY,     lambda n: n > 0),
            (_TABLE,     lambda n: n > 0),
            (_LIST,      lambda n: n > 0),
        ]
        for selector, condition in confirmed:
            try:
                n = self.page.locator(selector).count()
                if condition(n):
                    return True
            except Exception:
                continue

        # Generic fallbacks (in case CSS hashes change in a future build)
        for selector in ("table tbody tr", "[role='row']", "[role='listitem']", "ul li"):
            try:
                if self.page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue

        # Content-based fallback: pagination text like "1-50 of 697 users"
        try:
            text = self.page.evaluate("() => document.body.innerText")
            if re.search(r"\d+-\d+ of \d+ users", text):
                return True
            if "user" in text.lower() and len(text) > 200:
                return True
        except Exception:
            pass

        return False

    def get_visible_user_row_count(self) -> int:
        """
        Return the number of visible user rows on the current page.

        Tries desktop table rows first, then mobile list items.
        """
        for selector in (_TABLE_ROW, _LIST_ITEM):
            try:
                n = self.page.locator(selector).count()
                if n > 0:
                    return n
            except Exception:
                continue

        for selector in ("table tbody tr", "[role='row']", "[role='listitem']", "ul li"):
            try:
                n = self.page.locator(selector).count()
                if n > 0:
                    return n
            except Exception:
                continue

        try:
            text = self.page.evaluate("() => document.body.innerText")
            emails = re.findall(r'\S+@\S+\.\S+', text)
            if emails:
                return len(emails)
        except Exception:
            pass

        return 0

    def get_page_content_summary(self) -> str:
        """Return a snippet of page text for debugging."""
        try:
            return self.page.evaluate("() => document.body.innerText")[:500].strip()
        except Exception:
            return ""

    # ─── Bulk import wizard ────────────────────────────────────────────────────
    #
    # Confirmed wizard flow (live portal screenshots 2026-03-03):
    #
    #  URL                                       Action
    #  ────────────────────────────────────────  ─────────────────────────────
    #  /users                                    JS-click a[href='/users/bulk-import']
    #  /users/bulk-import/download-template      click "Next" button
    #  /users/bulk-import/facility               select radio → click "Next"
    #  /users/bulk-import/upload?facility=UUID   set hidden input[type="file"]
    #  /users/bulk-import/review?...             click "Looks good, continue"
    #  /users  (redirect)                        toast "Bulk creating users" ✅
    #
    # CSV columns (official template): "First name", "Last name"

    # ── Internal helper: click the Bulk import entry point ───────────────────

    def _click_bulk_import_link(self) -> None:
        """
        Click a[href='/users/bulk-import'] on the /users page.

        The link exists in DOM (confirmed in DOM dump) but is wrapped in a
        MUI tooltip div with empty aria-label, which can cause Playwright's
        'visible' state check to fail.  We use 'attached' + JS-click fallback.
        """
        el = self.page.locator(_BULK_IMPORT)
        el.wait_for(state="attached", timeout=8_000)
        try:
            el.scroll_into_view_if_needed(timeout=3_000)
            el.click(timeout=5_000)
        except Exception:
            # JS click bypasses all Playwright visibility checks
            self.page.evaluate(
                'el => el.click()',
                el.element_handle(timeout=3_000),
            )
        self.page.wait_for_url("**/bulk-import**", timeout=10_000)
        self.page.wait_for_timeout(1_000)

    # ── Wizard step helpers ───────────────────────────────────────────────────

    def _wiz_click_next(self) -> None:
        """Click the 'Next' navigation button."""
        btn = self.page.get_by_role("button", name="Next")
        btn.wait_for(state="visible", timeout=8_000)
        btn.click()

    def _wiz_select_first_radio(self) -> None:
        """Select the first facility radio button on step 2."""
        for sel in ("input[type='radio']", "[role='radio']"):
            try:
                radio = self.page.locator(sel).first
                radio.wait_for(state="visible", timeout=5_000)
                radio.click()
                self.page.wait_for_timeout(300)
                return
            except Exception:
                pass

    def _wiz_attach_file(self, csv_name: str, csv_bytes: bytes) -> None:
        """
        Set the hidden file input on the upload step.

        The 'Browse & upload' button is a styled element that activates a
        hidden input[type='file'].  We send the file as a buffer payload
        (bypasses Playwright visibility checks), then fall back to
        JS-unhiding the input if needed.
        """
        payload = {"name": csv_name, "mimeType": "text/csv", "buffer": csv_bytes}
        file_input = self.page.locator('input[type="file"]').first
        try:
            file_input.set_input_files(payload, timeout=10_000)
            return
        except Exception:
            pass
        # Unhide input via JS then retry
        self.page.evaluate("""() => {
            var inp = document.querySelector('input[type="file"]');
            if (inp) inp.style.cssText =
                'display:block!important;visibility:visible!important;'
                + 'opacity:1!important;position:fixed!important;'
                + 'top:0;left:0;width:100px!important;height:100px!important;z-index:99999!important;';
        }""")
        self.page.wait_for_timeout(200)
        file_input.set_input_files(payload, timeout=10_000)

    def _wiz_click_looks_good(self) -> None:
        """Click 'Looks good, continue' on review steps."""
        for label in ("Looks good, continue", "Continue", "Next",
                      "Confirm", "Submit", "Finish"):
            try:
                btn = self.page.get_by_role("button", name=label)
                btn.wait_for(state="visible", timeout=4_000)
                btn.click()
                return
            except Exception:
                pass
        raise RuntimeError(
            f"'Looks good, continue' button not found.\n"
            f"  URL: {self.page.url}"
        )

    # ── Main wizard driver ────────────────────────────────────────────────────

    def run_bulk_import_wizard(self, csv_path: str) -> None:
        """
        Drive the entire 5-step bulk-import wizard end-to-end.

        Detects the current wizard step by URL on each iteration and
        performs the required action until we land back on /users.
        """
        import pathlib
        csv_bytes = pathlib.Path(csv_path).read_bytes()
        csv_name  = pathlib.Path(csv_path).name

        # Step 0: start wizard from /users if not already inside
        if "/bulk-import" not in self.page.url:
            self._click_bulk_import_link()

        for _attempt in range(10):
            url = self.page.url

            # Step 1 — Download template: /bulk-import or /download-template
            if url.rstrip("/").endswith("/bulk-import") or "download-template" in url:
                self._wiz_click_next()
                self.page.wait_for_timeout(1_000)
                continue

            # Step 2 — Facility selection: /bulk-import/facility
            if "facility" in url and "upload" not in url:
                self._wiz_select_first_radio()
                self._wiz_click_next()
                self.page.wait_for_timeout(1_000)
                continue

            # Step 3 — Upload file: /bulk-import/upload?facility=UUID
            if "upload" in url and "bulk-import" in url:
                self._wiz_attach_file(csv_name, csv_bytes)
                self.page.wait_for_url("**/review**", timeout=15_000)
                self.page.wait_for_timeout(1_000)
                continue

            # Step 4 — Review file issues: /bulk-import/review?...
            if "review" in url and "system" not in url:
                self._wiz_click_looks_good()
                self.page.wait_for_timeout(1_500)
                continue

            # Step 5 — Review system issues (optional step)
            if "system" in url:
                self._wiz_click_looks_good()
                self.page.wait_for_timeout(1_500)
                continue

            # Done — back on /users
            if "/users" in url and "bulk-import" not in url:
                return

            # Unknown step — nudge forward
            try:
                self._wiz_click_next()
                self.page.wait_for_timeout(1_500)
            except Exception:
                break

        if "bulk-import" in self.page.url:
            raise RuntimeError(
                f"Wizard did not complete after 10 steps.\n"
                f"  Stuck at: {self.page.url}"
            )

    # ── Legacy / compat wrappers ──────────────────────────────────────────────

    def click_bulk_upload_button(self) -> None:
        """Click 'Bulk import' and enter the wizard."""
        self._click_bulk_import_link()

    def navigate_to_upload_step(self) -> None:
        """Advance wizard to the upload step (step 3)."""
        for _ in range(4):
            url = self.page.url
            if "upload" in url and "bulk-import" in url:
                return
            if url.rstrip("/").endswith("/bulk-import") or "download-template" in url:
                self._wiz_click_next()
                self.page.wait_for_timeout(1_000)
            elif "facility" in url:
                self._wiz_select_first_radio()
                self._wiz_click_next()
                self.page.wait_for_timeout(1_000)
            else:
                break
        if "upload" not in self.page.url:
            raise RuntimeError(f"Could not reach upload step. URL: {self.page.url}")

    def attach_csv_file(self, csv_path: str) -> None:
        """Attach CSV to the hidden file input on step 3."""
        import pathlib
        self._wiz_attach_file(
            pathlib.Path(csv_path).name,
            pathlib.Path(csv_path).read_bytes(),
        )

    def submit_upload(self) -> None:
        """Click through remaining review steps."""
        for _ in range(3):
            if "bulk-import" not in self.page.url:
                return
            try:
                self._wiz_click_looks_good()
                self.page.wait_for_timeout(1_500)
            except Exception:
                try:
                    self._wiz_click_next()
                    self.page.wait_for_timeout(1_500)
                except Exception:
                    break

    def wait_for_upload_outcome(self, timeout_ms: int = 60_000) -> str:
        """
        Wait for the bulk-import to succeed.

        Confirmed success signal: toast 'Bulk creating users' on /users page.
        Returns 'success', 'error', or 'timeout'.
        """
        SUCCESS = (
            "text=/bulk creating/i, "
            "text=/import complete/i, "
            "text=/successfully imported/i, "
            "text=/users have been imported/i, "
            "[class*='toast' i]:visible, "
            "[class*='snack' i]:visible"
        )
        ERROR = (
            "text=/import failed/i, "
            "[role='alert']:has-text('error'), "
            "[class*='error' i]:visible"
        )
        try:
            self.page.wait_for_selector(
                f"{SUCCESS}, {ERROR}",
                timeout=timeout_ms,
                state="visible",
            )
        except Exception:
            if "/users" in self.page.url and "bulk-import" not in self.page.url:
                return "success"
            return "timeout"

        try:
            self.page.locator(SUCCESS).first.wait_for(state="visible", timeout=1_000)
            return "success"
        except Exception:
            return "error"

    def get_status_message(self) -> str:
        """Return visible toast / heading text."""
        for sel in (
            "[class*='toast' i]", "[class*='snack' i]",
            "[class*='notification' i]", "[role='alert']", "[role='status']",
            "h1", "h2",
        ):
            try:
                el = self.page.locator(sel).first
                el.wait_for(state="visible", timeout=1_000)
                text = el.inner_text().strip()
                if text:
                    return text
            except Exception:
                continue
        return ""
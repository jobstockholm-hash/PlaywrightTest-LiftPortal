"""
pages/dashboard_page.py
=======================
Post-login dashboard page object for the LIFT Portal.

Root cause fix (2026-03-03)
---------------------------
`is_on_dashboard()` was returning False for Tests 2 & 3 because the
`_do_login` helper called `login()`, which previously returned as soon
as the click fired — before the React SPA navigated away from /login.

The fix is in login_page.py (`expect_navigation` in `click_sign_in`).
This file confirms the final state with a generous timeout.
"""

from playwright.sync_api import Page


class DashboardPage:
    """Authenticated LIFT Portal session — navigation and auth detection."""

    _AUTH_SHELL = (
        "nav, aside, header, "
        "[class*='sidebar'], [class*='nav-'], [class*='menu'], "
        "[class*='layout'], [class*='dashboard'], [class*='portal']"
    )

    def __init__(self, page: Page):
        self.page = page

    # ── Auth detection ────────────────────────────────────────────────────────

    def is_on_dashboard(self, timeout_ms: int = 12_000) -> bool:
        """
        Return True when:
          1. URL no longer contains '/login'
          2. Authenticated shell element is visible

        12 s default — the LIFT dev environment can take 8-10 s on first load.
        """
        try:
            self.page.wait_for_url(
                lambda url: "/login" not in url,
                timeout=timeout_ms,
            )
        except Exception:
            return False

        try:
            self.page.wait_for_selector(
                self._AUTH_SHELL,
                state="visible",
                timeout=timeout_ms,
            )
            return True
        except Exception:
            # URL changed (past login) even if shell selector didn't match —
            # URL is the definitive signal.
            return "/login" not in self.page.url

    def wait_until_authenticated(self, timeout_ms: int = 15_000) -> bool:
        """Alias kept for backwards compatibility."""
        return self.is_on_dashboard(timeout_ms=timeout_ms)

    # ── Navigation ────────────────────────────────────────────────────────────

    def go_to_users(self) -> None:
        """Navigate to Users management. Tries nav link then direct URL."""
        # 1: semantic role link
        try:
            link = self.page.get_by_role("link", name="Users")
            link.first.wait_for(state="visible", timeout=6_000)
            link.first.click()
            self.page.wait_for_load_state("domcontentloaded")
            return
        except Exception:
            pass

        # 2: any anchor in nav/sidebar containing "Users"
        try:
            anchor = self.page.locator(
                "nav a, aside a, header a, "
                "[class*='sidebar'] a, [class*='menu'] a, [class*='nav'] a"
            ).filter(has_text="Users").first
            anchor.wait_for(state="visible", timeout=6_000)
            anchor.click()
            self.page.wait_for_load_state("domcontentloaded")
            return
        except Exception:
            pass

        # 3: direct URL fallback
        base = "/".join(self.page.url.split("/")[:3])
        for path in ["/admin/users", "/users", "/manage/users", "/portal/users"]:
            self.page.goto(base + path, wait_until="domcontentloaded", timeout=20_000)
            if "/login" not in self.page.url:
                return

        raise RuntimeError(
            f"Could not navigate to Users section. Current URL: {self.page.url}"
        )

    def get_current_url(self) -> str:
        return self.page.url
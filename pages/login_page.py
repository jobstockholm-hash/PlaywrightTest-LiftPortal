"""
pages/login_page.py
===================
Page Object for the LIFT Portal login screen.

Selector strategy
-----------------
The LIFT portal is a React SPA.  The login form contains:
  • A text input labelled "Username or email address"
  • A password input
  • A "Sign in" submit button

We use the *most specific, least fragile* selectors:
  1. Playwright's `get_by_label` / `get_by_role` where possible — these
     survive CSS-class renames and work across languages.
  2. CSS attribute selectors as fallback.
"""

import time
from playwright.sync_api import Page
from typing import Optional


class LoginPage:
    """Login / authentication page of the LIFT Portal."""

    def __init__(self, page: Page, base_url: str):
        self.page     = page
        self.base_url = base_url.rstrip("/")

    # ── Navigation ────────────────────────────────────────────────────────────

    def navigate(self) -> None:
        """
        Go to the login page and wait until the form is interactive.
        We use 'domcontentloaded' (not 'networkidle') because React SPAs
        keep long-lived websocket / XHR connections that prevent networkidle
        from ever firing.
        """
        login_url = f"{self.base_url}/login"
        self.page.goto(login_url, wait_until="domcontentloaded", timeout=30_000)
        # Wait for the password field — guaranteed to exist on this page
        self.page.locator('input[type="password"]').wait_for(
            state="visible", timeout=15_000
        )

    # ── Locators (properties so they're always fresh) ─────────────────────────

    @property
    def _username_input(self):
        """
        The username/email field.  The LIFT portal renders a plain <input>
        (not type="email") labelled "Username or email address".
        We try get_by_label first; if absent fall back to the first
        non-password text input.
        """
        try:
            loc = self.page.get_by_label("Username or email address")
            loc.wait_for(state="visible", timeout=3_000)
            return loc
        except Exception:
            # Fallback: first input that is NOT a password field
            return self.page.locator(
                'input:not([type="password"]):not([type="hidden"]):not([type="checkbox"])'
            ).first

    @property
    def _password_input(self):
        return self.page.locator('input[type="password"]').first

    @property
    def _sign_in_button(self):
        """
        The submit button.  LIFT portal uses the exact text "Sign in".
        get_by_role is the most robust selector here.
        """
        try:
            return self.page.get_by_role("button", name="Sign in")
        except Exception:
            return self.page.locator(
                'button[type="submit"], button:has-text("Sign in")'
            ).first

    @property
    def _error_locator(self):
        return self.page.locator('[role="alert"], .error, [class*="error"], [class*="alert"]').first

    # ── Actions ───────────────────────────────────────────────────────────────

    def fill_username(self, username: str) -> None:
        self._username_input.click()
        self._username_input.fill(username)

    def fill_password(self, password: str) -> None:
        self._password_input.click()
        self._password_input.fill(password)

    def click_sign_in(self) -> None:
        """
        Click Sign in AND wait for the page to navigate away from /login.
        Using expect_navigation ensures we don't return until the redirect
        has actually started — this is the key fix for Tests 2 & 3.
        """
        with self.page.expect_navigation(
            url=lambda url: "/login" not in url,
            timeout=15_000,
            wait_until="domcontentloaded",
        ):
            self._sign_in_button.click()

    def login(self, username: str, password: str) -> None:
        """
        Complete login flow: fill credentials, submit, and wait until the
        portal has redirected away from /login before returning.
        """
        self.fill_username(username)
        self.fill_password(password)
        self.click_sign_in()

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_login_form_visible(self) -> bool:
        try:
            self._password_input.wait_for(state="visible", timeout=10_000)
            return True
        except Exception:
            return False

    def get_error_text(self) -> Optional[str]:
        try:
            self._error_locator.wait_for(state="visible", timeout=3_000)
            return self._error_locator.inner_text()
        except Exception:
            return None
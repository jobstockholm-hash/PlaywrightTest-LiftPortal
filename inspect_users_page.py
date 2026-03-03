"""
inspect_users_page.py
=====================
ONE-TIME diagnostic script — run this to discover the real DOM structure
of the LIFT Portal /users page so selectors can be updated.

Usage:
    python3 inspect_users_page.py

Output:
    - Prints all unique tag+class combinations found on the page
    - Saves a full-page screenshot to reports/screenshots/users_page_dom.png
    - Saves the full HTML to reports/users_page.html for inspection in browser
"""

import os, re, json
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from collections import Counter

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://lift-dev.training")
USERNAME = os.getenv("ADMIN_USERNAME", "per.helge.aasland+dev-site-admin@laerdal.com")
PASSWORD = os.getenv("ADMIN_PASSWORD", "asahiisverycool")

Path("reports/screenshots").mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.set_default_timeout(30_000)

    # ── Login ──────────────────────────────────────────────────────────────
    print(f"Navigating to {BASE_URL}/login ...")
    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
    page.locator('input[type="password"]').wait_for(state="visible")

    try:
        page.get_by_label("Username or email address").fill(USERNAME)
    except Exception:
        page.locator('input:not([type="password"]):not([type="hidden"])').first.fill(USERNAME)

    page.locator('input[type="password"]').fill(PASSWORD)

    with page.expect_navigation(url=lambda u: "/login" not in u, timeout=15_000):
        page.get_by_role("button", name="Sign in").click()

    print(f"Logged in. URL: {page.url}")

    # ── Navigate to /users ─────────────────────────────────────────────────
    page.goto(f"{BASE_URL}/users", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)   # let React render
    print(f"Users page URL: {page.url}")

    # ── Screenshot ─────────────────────────────────────────────────────────
    ss = "reports/screenshots/users_page_dom.png"
    page.screenshot(path=ss, full_page=True)
    print(f"\n📸 Screenshot saved: {ss}")

    # ── Save HTML ──────────────────────────────────────────────────────────
    html = page.content()
    Path("reports/users_page.html").write_text(html, encoding="utf-8")
    print(f"📄 Full HTML saved: reports/users_page.html")

    # ── Dump all elements with class names (first 80) ──────────────────────
    print("\n═══ ALL ELEMENTS WITH CLASS NAMES (first 80) ═══")
    elements = page.evaluate("""() => {
        const els = Array.from(document.querySelectorAll('*'));
        return els
            .filter(el => el.className && typeof el.className === 'string' && el.className.trim())
            .slice(0, 80)
            .map(el => ({
                tag: el.tagName.toLowerCase(),
                cls: el.className.trim().split(/ +/).slice(0,4).join(' '),
                text: el.textContent.trim().slice(0, 60),
                role: el.getAttribute('role') || '',
                id: el.id || '',
                dataTestid: el.getAttribute('data-testid') || ''
            }));
    }""")
    for e in elements:
        print(f"  <{e['tag']}> role={e['role']} id={e['id']} testid={e['dataTestid']}")
        print(f"    class: {e['cls']}")
        print(f"    text:  {e['text'][:60]}")

    # ── Specifically look for list/table-like structures ───────────────────
    print("\n═══ TABLE / LIST / GRID ELEMENTS ═══")
    list_els = page.evaluate("""() => {
        const tags = ['table','ul','ol','dl','tbody','tr','td','th','li'];
        const roles = ['grid','list','listitem','row','cell','rowgroup'];
        const result = [];
        
        // by tag
        tags.forEach(tag => {
            document.querySelectorAll(tag).forEach(el => {
                result.push({
                    tag: el.tagName.toLowerCase(),
                    cls: el.className,
                    role: el.getAttribute('role') || '',
                    text: el.textContent.trim().slice(0,60),
                    count: el.children.length
                });
            });
        });
        
        // by role
        roles.forEach(role => {
            document.querySelectorAll(`[role="${role}"]`).forEach(el => {
                result.push({
                    tag: el.tagName.toLowerCase(),
                    cls: el.className,
                    role: role,
                    text: el.textContent.trim().slice(0,60),
                    count: el.children.length
                });
            });
        });
        
        return result.slice(0, 40);
    }""")
    if list_els:
        for e in list_els:
            print(f"  <{e['tag']}> role={e['role']} children={e['count']}")
            print(f"    class: {e['cls'][:80]}")
            print(f"    text:  {e['text']}")
    else:
        print("  ⚠️  No standard table/list/grid elements found!")
        print("  → The portal uses a custom React component.")

    # ── Look for any div/section that might be a user row ─────────────────
    print("\n═══ DIVS CONTAINING USER-LIKE DATA (email pattern) ═══")
    user_rows = page.evaluate("""() => {
        const allDivs = Array.from(document.querySelectorAll('div, li, tr, article'));
        return allDivs
            .filter(el => /@/.test(el.textContent) || /user|member|name/i.test(el.getAttribute('class') || ''))
            .slice(0, 20)
            .map(el => ({
                tag: el.tagName.toLowerCase(),
                cls: (el.className || '').trim().slice(0, 80),
                text: el.textContent.trim().slice(0, 100),
                role: el.getAttribute('role') || '',
                dataTestid: el.getAttribute('data-testid') || ''
            }));
    }""")
    for e in user_rows:
        print(f"  <{e['tag']}> role={e['role']} testid={e['dataTestid']}")
        print(f"    class: {e['cls']}")
        print(f"    text:  {e['text'][:80]}")

    # ── Look for buttons (Import / Bulk upload) ────────────────────────────
    print("\n═══ ALL BUTTONS & LINKS ON THE PAGE ═══")
    buttons = page.evaluate("""() => {
        const els = Array.from(document.querySelectorAll('button, a, [role="button"]'));
        return els.map(el => ({
            tag: el.tagName.toLowerCase(),
            text: el.textContent.trim().slice(0, 60),
            cls: (el.className || '').slice(0, 60),
            href: el.getAttribute('href') || '',
            dataTestid: el.getAttribute('data-testid') || ''
        })).filter(e => e.text).slice(0, 40);
    }""")
    for b in buttons:
        print(f"  <{b['tag']}> text='{b['text']}' href={b['href']} testid={b['dataTestid']}")

    # ── Look for headings ──────────────────────────────────────────────────
    print("\n═══ HEADINGS ═══")
    headings = page.evaluate("""() =>
        Array.from(document.querySelectorAll('h1,h2,h3,h4'))
             .map(el => ({tag: el.tagName, text: el.textContent.trim()}))
    """)
    for h in headings:
        print(f"  <{h['tag']}> {h['text']}")

    browser.close()
    print("\n✅ Done. Open reports/users_page.html in your browser for full DOM inspection.")
    print("   Then share the output of this script to get exact selectors.")

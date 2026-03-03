# Laerdal LIFT Portal – UI Test Automation

Playwright + Python + pytest automation suite for **https://lift-dev.training**.

---

## Quick start (5 commands)

```bash
# 1. Clone
git clone https://github.com/your-org/laerdal-lift-tests.git
cd laerdal-lift-tests

# 2. Virtual environment
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1

# 3. Dependencies
pip install -r requirements.txt

# 4. Playwright browser
playwright install chromium

# 5. Run
cp .env.example .env          # credentials already set; change if needed
pytest
```

Open `reports/test_report.html` in any browser for the full report with screenshots.

---

## Why Playwright + Python?

| | Playwright ✅ | Selenium | Cypress |
|---|---|---|---|
| Auto-wait (no `sleep`) | ✅ | ❌ manual | ✅ |
| Python first-class | ✅ | ✅ | ❌ |
| File upload (headless) | ✅ native | ⚠️ workaround | ⚠️ |
| React SPA friendly | ✅ | ⚠️ | ✅ |
| Screenshot on failure | ✅ 1 line | ⚠️ | ✅ |
| GitHub Actions support | ✅ official | ✅ | ✅ |

---

## Project layout

```
laerdal-lift-tests/
├── pages/
│   ├── login_page.py       ← login form selectors & actions
│   ├── dashboard_page.py   ← post-login navigation
│   └── users_page.py       ← user list + bulk upload
├── tests/
│   └── test_lift_portal.py ← all 3 test cases
├── utils/
│   └── csv_generator.py    ← generates 35-user CSV
├── reports/
│   └── screenshots/        ← auto-created; one PNG per step
├── conftest.py             ← fixtures + auto-screenshot on failure
├── pytest.ini
├── requirements.txt
├── .env.example
└── .github/workflows/ui-tests.yml
```

---

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `BASE_URL` | `https://lift-dev.training` | Portal URL |
| `ADMIN_USERNAME` | *(see .env.example)* | Login email |
| `ADMIN_PASSWORD` | *(see .env.example)* | Password |
| `LOGIN_TIMEOUT_MS` | `5000` | SLA for Test #1 |
| `DEFAULT_TIMEOUT_MS` | `30000` | General wait timeout |
| `HEADLESS` | `true` | `false` = visible browser |
| `SLOW_MO` | `0` | ms delay per action (demo mode) |

---

## Running tests

```bash
# All tests
pytest

# One test class
pytest tests/test_lift_portal.py::TestLogin
pytest tests/test_lift_portal.py::TestUserList
pytest tests/test_lift_portal.py::TestBulkUpload

# Watch the browser (great for debugging)
HEADLESS=false pytest

# Slow motion – easy to follow for demos
HEADLESS=false SLOW_MO=600 pytest

# Run only smoke tests
pytest -m smoke

# Stop at first failure
pytest -x
```

---

## Test summary

### Test #1 – Login within 5 seconds
| Step | Action | Assertion |
|---|---|---|
| 1 | Navigate to `/login` | Login form is visible |
| 2 | Fill credentials | Fields accepted input |
| 3 | Click "Sign in" | Dashboard renders |
| 4 | Measure elapsed time | ≤ 5 000 ms |

### Test #2 – User list visible
| Step | Action | Assertion |
|---|---|---|
| 1 | Log in | Dashboard URL, not `/login` |
| 2 | Navigate to Users | Page loaded, URL changed |
| 3 | Inspect list | Table has ≥ 1 row |

### Test #3 – Bulk upload 35 users
| Step | Action | Assertion |
|---|---|---|
| 1 | Generate CSV | File exists on disk |
| 2 | Log in | Dashboard confirmed |
| 3 | Go to Users | Page loaded |
| 4 | Open bulk-upload | Dialog/drawer visible |
| 5 | Attach CSV | File input accepted |
| 6 | Submit | Request sent |
| 7 | Wait for feedback | Success message shown |

---

## Reports & screenshots

Every test step saves a PNG to `reports/screenshots/`:
```
t1_s1_login_form_1717245312.png
t1_s3_post_login_1717245315.png
FAIL__test_login_within_5_seconds__20240601_143512.png   ← failure
```

Screenshots are **embedded** in `reports/test_report.html`.

---

## CI/CD (GitHub Actions)

Add these three **repository secrets** (Settings → Secrets → Actions):

| Secret | Value |
|---|---|
| `BASE_URL` | `https://lift-dev.training` |
| `ADMIN_USERNAME` | *(admin email)* |
| `ADMIN_PASSWORD` | *(admin password)* |

The workflow runs on every push, every PR to `main`, and every weekday at 06:00 UTC.
The HTML report + screenshots are uploaded as a workflow artifact (30-day retention).

---

## If tests fail: fixing selectors

The portal is a React SPA — its class names can change after a frontend update.
**Selectors live in one place per page** (`pages/*.py`), so a single edit fixes all tests.

### Step-by-step debugging workflow

1. **Run with a visible browser to see what's happening:**
   ```bash
   HEADLESS=false SLOW_MO=500 pytest tests/test_lift_portal.py::TestLogin -s
   ```

2. **Open Playwright's interactive inspector to find the right selector:**
   ```bash
   python3 -c "
   from playwright.sync_api import sync_playwright
   with sync_playwright() as p:
       b = p.chromium.launch(headless=False)
       page = b.new_page()
       page.goto('https://lift-dev.training/login')
       input('Press Enter to close...')
   "
   ```
   Then right-click any element in the browser → Inspect → note the `id`, `name`,
   `data-testid`, or `aria-label`.

3. **Update the selector constant in the relevant page file**, e.g.:
   ```python
   # pages/login_page.py
   @property
   def _username_input(self):
       return self.page.locator('#username')   # ← your discovered selector
   ```

4. **Re-run the test** — the fix propagates to all tests automatically.

### Common selector patterns for the LIFT portal

The LIFT portal uses standard semantic HTML and ARIA attributes.  Prefer:

```python
page.get_by_role("button", name="Sign in")          # buttons
page.get_by_label("Username or email address")       # inputs
page.get_by_role("link", name="Users")               # nav links
page.get_by_role("row")                              # table rows
page.locator('[data-testid="..."]')                  # if data-testid exists
```

### Test #3 CSV columns

If bulk upload fails with a validation error, download the portal's own
CSV template (usually a link in the upload dialog) and update
`utils/csv_generator.py` to match its exact column names.

---

## Extending the suite

1. Add a new file `pages/my_feature_page.py` (copy an existing one).
2. Add a test class in `tests/test_lift_portal.py` (or a new `test_*.py` file).
3. Selectors are isolated — tests never reference CSS or XPath directly.

---

*Developed for Laerdal Medical – LIFT Portal Test Automation.*

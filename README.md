# Laerdal LIFT Portal – UI Test Automation

Playwright + Python + pytest automation suite for **https://lift-dev.training**.

---

## Quick start (5 commands)

```bash
# 1. Clone
git clone https://github.com/jobstockholm-hash/PlaywrightTest-LiftPortal.git
cd PlaywrightTest-LiftPortal

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

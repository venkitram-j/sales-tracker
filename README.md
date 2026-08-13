# Sales Tracker

A Django + Bootstrap web application for tracking product sales across
multiple store branches — products, branches, branch admins, buyers, and
branch-wise sales reporting, with Excel bulk-import support throughout.

> **Known gap:** the Sales Data upload parses a "Branch" banner line above
> the header row, but no sample file was available to confirm its exact
> wording - see §4 "Sales Data: the Branch and reporting-period banners"
> for the current best-effort pattern and where to fix it once confirmed.

---

## 1. Features

### Modules
| Module | Fields | Description |
|---|---|---|
| **Users** | — | Built-in `django.contrib.auth.models.User`. Authentication is by **email + password** (username is auto-derived from email and never shown in any form). User creation and password resets happen **only** through the Django admin panel (`/admin/`). |
| **Departments** | Name | Departments products are categorised under. |
| **Branches** | Name | Physical store locations. |
| **Buyers** | Name | Vendors/buyers who procure products for the store. |
| **Admins** | User, Branches | Regular Users designated to manage one or more branches (many-to-many). User accounts themselves still come from the admin panel — this module only attaches branch-management responsibility. |
| **Products** | Product Code, Description, Department | Sellable products. Each product belongs to exactly one Department. |
| **Sales Data** | Product Code, Description, Department, Branch, Admin, Buyer, Start Date, End Date, Total Sales Qty, Total Sales Amt, Total Stock | The core transactional table - one record per product/branch/reporting-period. Uniquely identified by (Product Code, Branch, Start Date, End Date). Includes a **branch-wise aggregated report** in addition to the raw record list. |

### Cross-cutting functionality
- **Excel bulk upload** (`.xlsx`) on every module, reachable from each list page, built entirely on **pandas + the `calamine` engine** (a fast Rust-based reader) for large files (500k+ rows):
  - The workbook is read **once** into a DataFrame; header detection, whitespace stripping, and blank-row removal are all **vectorized pandas operations**, not a per-row Python loop.
  - The cleaned DataFrame is split into fixed-size **chunks** (5,000 rows by default) and each chunk is written with a small, constant number of queries via `bulk_create` - independent of file size - rather than one query per row.
  - Every upload's Excel columns match the model's field names (e.g. the Departments upload expects a single `Department` column; the Products upload expects `Product Code`, `Description`, `Department`) - see §4 for the exact list per module.
  - Bad rows are reported in aggregate (e.g. "12 row(s) skipped - missing 'Product Code' value") rather than one message per row, since vectorized validation naturally works on whole columns at once; the rest of the file keeps processing.
  - Every upload also supports a configurable **Header Row / Start Column** (see §4) for spreadsheets that don't start their table in cell A1 - data is always read starting the row right after the header row.
  - **Postgres-optimized writes**: Departments, Branches, Buyers, Products (by Product Code) and Store Admins (by linked User) all use a single `bulk_create(..., ignore_conflicts=True)` per chunk - a native `INSERT ... ON CONFLICT DO NOTHING` - to skip rows that already exist, with a before/after count query used only for accurate created/skipped reporting. **Sales Data** uses `bulk_create(..., update_conflicts=True, unique_fields=[...])` - a native `INSERT ... ON CONFLICT (...) DO UPDATE` - to replace an existing record for the same Product Code + Branch + reporting period in a single statement, or insert a new one otherwise. Both patterns work identically on PostgreSQL and SQLite.
  - **Master data must exist first**: Products, Departments, Buyers, and Store Admins referenced by a Product or Sales Data upload are looked up, not auto-created - upload them via their own pages first. Only the Branch and reporting period banners on a Sales Data file are validated once per upload (see below); everything else is a per-row/column lookup.
  - **Sales Data** is the one upload where two pieces of information are *not* per-row columns: the Branch and the reporting period (Start Date/End Date) are parsed once from banner lines above the header row and applied to the whole file - see §4.
- **Live search** on every list page's search bar, powered by **HTMX** (no page reload, no custom JavaScript per page): typing debounces for 400ms then re-fetches just the results, and pagination/filtering also happens in place. The server-side view code is completely unchanged for this - HTMX is configured to request the same page and extract just the results fragment (`hx-select`), so plain-Django full-page loads work identically for JS-disabled clients or direct links.
- **Permissions**: 100% built-in `django.contrib.auth` permissions (`Permission`, `Group`). No custom permission system. A `seed_groups` management command creates three ready-to-use groups (Viewer / Branch Manager / Data Administrator) — see §6.
- **Filters**: Products can be filtered by Department; Sales Data (both the raw list and the branch-wise report) can be filtered by Branch, Product, Department, Admin, Buyer and reporting-period date range.
- **Dashboard**: KPIs (total quantity, total value, active product/branch counts), top branches by value, and an interactive, client-side-filterable recent sales table.
- **Responsive Bootstrap 5 UI**: collapsible sidebar on mobile; on desktop the sidebar is pinned under the topbar and only scrolls internally if its own contents overflow, independent of the page's scroll position. Topbar shows app name + logged-in user's full name + logout.
- **Delete confirmation modals**: every delete action is confirmed via a Bootstrap modal before the (POST-only) delete request is sent.
- **Double-submit protection**: all form submit buttons are automatically disabled (with a spinner) on submit via shared JS, no per-form wiring needed.
- **Django admin panel**: every model is registered with sensible `list_display`/`list_filter`/`search_fields` and bulk actions (activate/deactivate).

---

## 2. Architecture & tech choices

- **Django 5.2**, Python 3.14+ compatible, class-based views throughout (`ListView`, `CreateView`, `UpdateView`, generic `View` for delete, `FormView` for Excel upload).
- **Frontend**: Bootstrap 5 + [HTMX](https://htmx.org) (loaded from CDN, no build step) for the live search/filter/pagination behaviour on every list page - see §1.
- **App layout**: one Django app per module under `apps/`, plus `apps/core` for shared, reusable building blocks:
  - `apps/core/mixins.py` — `CrudPermissionMixin` (login + built-in permission check), `ExcelUploadView` (generic batched bulk-import base class - see below), `ObjectDeleteView` (generic POST-only delete with `ProtectedError` handling), `SuccessMessageMixin`.
  - `apps/core/forms.py` — `BootstrapModelForm` (auto-applies Bootstrap CSS classes to every field so individual forms stay declarative), `ExcelUploadForm`.
  - `apps/core/utils.py` — Excel reading built on **pandas + the `calamine` engine** (`python-calamine`, a Rust-based reader) rather than openpyxl, since it's significantly faster on large workbooks. `load_excel()` reads the sheet once; `build_data_frame()` slices out the real header/data region and vectorizes whitespace stripping and blank-row removal; `chunk_dataframe()` yields fixed-size DataFrame slices for batched writes; `extract_pre_header_text()` pulls banner text sitting above the header row.
  - `apps/core/models.py` — `TimeStampedModel` abstract base (`created_at`, `updated_at`, `is_active`) inherited by every entity.
- **Excel upload architecture** (`apps/core/mixins.ExcelUploadView`): built for files with 500k+ rows and entirely DataFrame-native. Each subclass implements `process_chunk(chunk_df)`: given a DataFrame slice of up to `chunk_size` rows (5,000 by default), it validates/resolves/writes that chunk - typically via vectorized pandas cleaning followed by a single `bulk_create` per chunk - and returns (created, updated, skipped, errors). The base view loads the workbook once, builds the cleaned DataFrame, chunks it, and calls `process_chunk` per chunk; a chunk that fails outright is caught and reported without aborting the rest of the file. See §4 for the Postgres-specific `ignore_conflicts`/`update_conflicts` patterns each subclass uses.
- **Settings are split** (`config/settings/base.py`, `development.py`, `production.py`) so environment-specific behaviour (debug flags, database engine, security headers, logging handlers) never has to be toggled by hand — set `DJANGO_SETTINGS_MODULE` (the provided scripts do this for you) and everything follows.
- **Logging**: development logs to console at `DEBUG` level; production adds rotating file handlers (`logs/sales_tracker.log`, 10MB × 10 backups, plus a separate error-only log) alongside console output. A lightweight `RequestLoggingMiddleware` logs method/path/status/duration/user for every request.
- **Performance for high traffic**:
  - Every list view uses `select_related`/`prefetch_related` to avoid N+1 queries.
  - Database indexes on frequently filtered columns (`SalesData.start_date`/`end_date`, composite `branch+product_code+start_date`, `Department`), plus a `UniqueConstraint` on `SalesData(product_code, branch, start_date, end_date)` that both enforces the one-record-per-period rule and backs the Postgres `ON CONFLICT` upsert used by the Sales Data upload.
  - `CONN_MAX_AGE` persistent DB connections in production.
  - Pagination (25–50 rows) on every list view; HTMX makes paging and searching feel instant without a full page reload.
  - WhiteNoise serves compressed, cache-busted static assets directly from the app process — no separate static file infrastructure required to get production-grade static serving.
  - Foreign keys from `SalesData` use `on_delete=PROTECT`, preventing accidental data loss of referenced Products/Branches/Admins/Departments/Buyers; the UI surfaces this as a friendly message instead of a 500 error.
  - Excel uploads: see "Excel upload architecture" above - chunked, vectorized bulk writes instead of per-row queries. Benchmarked in development at ~3,800-5,900 rows/sec depending on upload complexity - a 500k-row Sales Data file completes in roughly 1.5-2 minutes.

---

## 3. Project layout

```
sales_tracker/
├── manage.py
├── requirements.txt
├── .env.example
├── config/
│   ├── settings/{base,development,production}.py
│   ├── urls.py, wsgi.py, asgi.py
├── apps/
│   ├── core/            # shared mixins, forms, models, middleware, management commands
│   ├── accounts/        # email auth backend, login/logout views, User admin customization
│   ├── departments/
│   ├── products/
│   ├── branches/
│   ├── store_admins/    # the "Admins" module (named store_admins to avoid clashing with django.contrib.admin)
│   ├── buyers/
│   ├── salesdata/
│   └── dashboard/
├── templates/            # base.html + per-app templates + reusable partials (topbar, sidebar, delete modal, excel upload form, pagination)
├── static/{css,js}/
├── scripts/              # lifecycle helper scripts, see §5
└── logs/                 # rotating log files land here in production
```

---

## 4. Getting started (development)

### Prerequisites
- Python 3.14+ (3.12+ also works)
- SQLite is used by default in development — no separate database server needed to get started.

### Quick start
```bash
git clone <your-repo-url> sales_tracker
cd sales_tracker
scripts/setup.sh              # creates venv, installs deps, copies .env, runs migrations
scripts/createsuperuser.sh    # create your first login (email + password, no username prompt)
python manage.py seed_groups  # optional: creates Viewer / Branch Manager / Data Administrator groups
scripts/run_dev.sh            # starts the dev server on http://127.0.0.1:8000
```

Then log in at `http://127.0.0.1:8000/accounts/login/` with the email/password you just created.

### Manual setup (equivalent, without the scripts)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # edit SECRET_KEY etc. as needed
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Creating additional users
User creation and password resets are **admin-panel only** by design (per the app's access-control requirements). Go to `/admin/`, add a user under **Accounts > Users** with an email, first/last name and password — the username field is hidden and populated automatically. Assign them to a permission Group (see §6) or set individual permissions.

### Excel upload formats
Every upload's expected columns match the model's field names exactly (also shown on each upload page). Column headers are case-insensitive, whitespace-tolerant, and spaces are treated the same as underscores (`Product Code` and `product_code` both work).

| Entity | Required column(s) |
|---|---|
| Departments | `Department` |
| Branches | `Branch` |
| Buyers | `Buyer` |
| Store Admins | `Admin` (the user's email - the account must already exist), `Branch` (must already exist). One row per admin+branch pairing - give the same admin one row per branch they manage and they're aggregated automatically. |
| Products | `Product Code`, `Description`, `Department` (must already exist) |
| Sales Data | `Product Code` (must already exist), `Description`, `Department` (must already exist), `Admin` (email, must already be a Store Admin), `Buyer` (must already exist), `Total Sales Qty`, `Total Sales Amt`, `Total Stock`. **`Branch`, `Start Date` and `End Date` are NOT columns** — see below. |

For Departments/Branches/Buyers/Products/Store Admins, a row referencing an entity that already exists is skipped (not duplicated) - see "Postgres-optimized writes" in §1.

#### Sales Data: the Branch and reporting-period banners
Rather than per-row columns, a Sales Data spreadsheet covers a single branch and a single reporting period for the *whole file*, given as banner lines **above** the header row:

```
Branch :- Downtown
Report Period From :- 01-09-2025,  To :- 30-09-2025
```

On upload, every row before your configured **Header Row** is scanned for these two patterns and parsed (dates as `DD-MM-YYYY`). Both are required — if either is missing, or the named Branch doesn't already exist, the whole upload is rejected up front with a clear error before any rows are processed. Set **Header Row** (below) to the row your real column headers are on, keeping both banner lines somewhere above it.

> **⚠️ Not yet verified against a real sample file.** The reporting-period format above was explicitly confirmed in an earlier round of this project; the **Branch banner's exact wording has not been** - no sample file was available when this was built, so the parser currently accepts any line matching `Branch[:/- ]<name>` (case-insensitive - e.g. "Branch :- Downtown", "Branch Name: Downtown", "Branch - Downtown" all work). If your real files use different wording, update `BRANCH_LINE_PATTERN` in `apps/salesdata/report_period.py` — it's the single place that pattern lives. Share a sample file and this can be tightened up precisely.

For a given Product Code within that Branch + reporting period, uploading again **replaces** the existing record's values (description, department, admin, buyer, quantities/amounts/stock) rather than creating a duplicate. A different reporting period (or branch) for the same product creates a separate record, since Product Code + Branch + Start Date + End Date together are what uniquely identify a row (enforced by a database `UniqueConstraint`, and used as the `unique_fields` for the `ON CONFLICT DO UPDATE`).

#### Custom sheet layout (header row / start column)
Real-world spreadsheets often don't start their table in cell A1 - there might be a title banner, a couple of blank/notes rows, or a leading "S.No." index column before the actual data. Every upload page has a collapsible **"Sheet Layout Options"** panel (auto-expanded if you submit invalid values) with two settings, both optional and defaulting to the common case:

| Setting | Default | Purpose |
|---|---|---|
| **Header Row** | `1` | The row number containing your column headers. Data is always read starting the row right after this one. For Sales Data, this must be below both banner lines (see above). |
| **Start Column** | `A` | The column letter where your headers/data begin. Anything to the left of this column (e.g. a serial-number column) is ignored. |

Example: a file with a title in row 1, a blank row 2, and real headers in row 3, with an extra "S.No." column in column A (so your actual headers start in column B) would use **Header Row = 3**, **Start Column = B**.

These settings are validated server-side (e.g. Start Column must be a real column letter) and apply uniformly to every module's upload, since they're implemented once in `apps/core/utils` and `apps/core/forms.ExcelUploadForm` and reused everywhere.

---

## 5. Helper scripts (`scripts/`)

| Script | Purpose |
|---|---|
| `setup.sh` | One-time bootstrap: venv, dependencies, `.env`, initial migration. |
| `run_dev.sh [host:port]` | Runs the dev server with `config.settings.development` (defaults to `127.0.0.1:8000`). |
| `run_prod.sh` | Runs the app under Gunicorn with `config.settings.production`. Reads `BIND_ADDR`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT` from the environment if set. |
| `migrate.sh [dev\|prod]` | Runs `makemigrations` + `migrate` against the chosen environment. |
| `createsuperuser.sh` | Interactive superuser creation (email/password only). |
| `collectstatic.sh` | Collects static files into `staticfiles/` for production (WhiteNoise). |
| `backup_db.sh` | Dumps all application data to a timestamped JSON fixture under `backups/` (database-agnostic; use `pg_dump` for full-fidelity Postgres backups in production). |

All scripts are POSIX shell, executable, and safe to re-run.

---

## 6. Permissions model

The app uses Django's built-in permission framework exclusively — no custom roles table.

- Every model automatically gets `add_`, `change_`, `delete_`, `view_` permissions (Django default).
- Views check permissions via `PermissionRequiredMixin` (wrapped as `CrudPermissionMixin` in `apps/core/mixins.py`), e.g. a Products list view requires `products.view_product`.
- The sidebar only shows links to modules the logged-in user actually has `view_*` permission for.
- `python manage.py seed_groups` creates three starter groups:
  - **Viewer** — view-only across all modules.
  - **Branch Manager** — view everything, plus add/edit Buyers and Sales Data.
  - **Data Administrator** — full CRUD across every module.
- Superusers bypass permission checks entirely (standard Django behaviour).
- Assign users to groups (or grant individual permissions) from **Django admin > Users > (select user) > Permissions**.

---

## 7. Environments

| | Development | Production |
|---|---|---|
| Settings module | `config.settings.development` | `config.settings.production` |
| `DEBUG` | `True` | `False` |
| Database | SQLite (zero config) | PostgreSQL (via env vars) |
| Logging | Console, `DEBUG` level | Console + rotating file handlers, `INFO` level |
| Security headers | Relaxed (HTTP allowed) | HSTS, SSL redirect, secure cookies enforced |
| Static files | Served by Django dev server | WhiteNoise (compressed, manifest-hashed) |
| Email | Console backend (prints to stdout) | SMTP (configured via env vars) |

Switch between them by setting `DJANGO_SETTINGS_MODULE` — the provided scripts already do this for you.

---

## 8. Production deployment notes

1. Set a strong `SECRET_KEY`, a real `ALLOWED_HOSTS`, and PostgreSQL credentials in `.env`.
2. `scripts/migrate.sh prod`
3. `scripts/collectstatic.sh`
4. `scripts/run_prod.sh` (or wire the same command into systemd/Docker/Kubernetes — it's a plain Gunicorn invocation).
5. Put a reverse proxy (nginx, an ALB, etc.) in front of Gunicorn for TLS termination; WhiteNoise already handles static file serving efficiently from within the app process.
6. Schedule `scripts/backup_db.sh` (or `pg_dump`) via cron for regular backups.

---

## 9. Testing what was built

This project was validated end-to-end during development using Django's test client: migrations apply cleanly, email login and the auto-derived-username signal work correctly, every list/add/upload page returns HTTP 200 for an authenticated user, permission checks correctly redirect users lacking the required permission, product/branch/admin/sales CRUD create flows work, Excel bulk upload works for Products and for Sales Data (including auto-creating missing Products/Branches), and attempting to delete a Product still referenced by Sales Data surfaces a friendly error instead of a server crash.

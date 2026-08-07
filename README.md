# Sales Tracker

A Django + Bootstrap web application for tracking product sales across
multiple store branches — products, branches, branch admins, buyers, and
branch-wise sales reporting, with Excel bulk-import support throughout.

---

## 1. Features

### Modules
| Module | Description |
|---|---|
| **Users** | Built-in `django.contrib.auth.models.User`. Authentication is by **email + password** (username is auto-derived from email and never shown in any form). User creation and password resets happen **only** through the Django admin panel (`/admin/`). |
| **Departments** | Manage departments products are categorised under (name, code, description). |
| **Products** | Manage sellable products (name, SKU, department, category, unit price, description). Each product belongs to exactly one Department. |
| **Branches** | Manage physical store locations (name, code, city, state, address). |
| **Admins** | Regular Users who have been designated to manage one or more branches. One admin can manage many branches (many-to-many). User accounts themselves still come from the admin panel — this module only attaches branch-management responsibility. |
| **Buyers** | Vendors/buyers who procure products for the store, optionally linked to the products they supply. |
| **Sales Data** | The core transactional table: product, branch, department, admin, buyer, sales quantity, sales value, total stock, and a reporting period (start date / end date). Includes a **branch-wise aggregated report** (totals per branch + product) in addition to the raw record list. |

### Cross-cutting functionality
- **Excel bulk upload** (`.xlsx`) on every module, reachable from each list page. Each row is processed independently (one bad row doesn't abort the batch); errors are reported back to the user with the offending row numbers. Every upload also supports a configurable **Header Row / Data Start Row / Start Column** (see §4) for spreadsheets that don't start their table in cell A1.
  - The **Sales Data** upload is special in two ways: it will **auto-create** missing Products, Branches, Departments and Buyers, and attach the referenced admin (an existing User) to the branch, so a single spreadsheet can seed most of the dataset (User accounts themselves must already exist — see Users above). It also **parses the reporting period** (start/end date) once from a banner line above the header row instead of from a per-row column — see §4.
  - Department is auto-populated on each Sales Data row: use an explicit `department_code`/`department_name` column if you have one, otherwise it's inferred from the referenced product's own department.
- **Permissions**: 100% built-in `django.contrib.auth` permissions (`Permission`, `Group`). No custom permission system. A `seed_groups` management command creates three ready-to-use groups (Viewer / Branch Manager / Data Administrator) — see §6.
- **Filters**: Products can be filtered by Department; Sales Data (both the raw list and the branch-wise report) can be filtered by Branch, Product, Department, Admin, Buyer and reporting-period date range.
- **Dashboard**: KPIs (total quantity, total value, active product/branch counts), top branches by value, and an interactive, client-side-filterable recent sales table.
- **Responsive Bootstrap 5 UI**: collapsible sidebar on mobile, topbar with app name + logged-in user's full name + logout.
- **Delete confirmation modals**: every delete action is confirmed via a Bootstrap modal before the (POST-only) delete request is sent.
- **Double-submit protection**: all form submit buttons are automatically disabled (with a spinner) on submit via shared JS, no per-form wiring needed.
- **Django admin panel**: every model is registered with sensible `list_display`/`list_filter`/`search_fields` and bulk actions (activate/deactivate).

---

## 2. Architecture & tech choices

- **Django 5.2**, Python 3.14+ compatible, class-based views throughout (`ListView`, `CreateView`, `UpdateView`, generic `View` for delete, `FormView` for Excel upload).
- **App layout**: one Django app per module under `apps/`, plus `apps/core` for shared, reusable building blocks:
  - `apps/core/mixins.py` — `CrudPermissionMixin` (login + built-in permission check), `ExcelUploadView` (generic bulk-import base class), `ObjectDeleteView` (generic POST-only delete with `ProtectedError` handling), `SuccessMessageMixin`.
  - `apps/core/forms.py` — `BootstrapModelForm` (auto-applies Bootstrap CSS classes to every field so individual forms stay declarative), `ExcelUploadForm`.
  - `apps/core/utils.py` — `iter_excel_rows()`, a single well-tested `openpyxl` row iterator reused by every upload view.
  - `apps/core/models.py` — `TimeStampedModel` abstract base (`created_at`, `updated_at`, `is_active`) inherited by every entity.
- **Settings are split** (`config/settings/base.py`, `development.py`, `production.py`) so environment-specific behaviour (debug flags, database engine, security headers, logging handlers) never has to be toggled by hand — set `DJANGO_SETTINGS_MODULE` (the provided scripts do this for you) and everything follows.
- **Logging**: development logs to console at `DEBUG` level; production adds rotating file handlers (`logs/sales_tracker.log`, 10MB × 10 backups, plus a separate error-only log) alongside console output. A lightweight `RequestLoggingMiddleware` logs method/path/status/duration/user for every request.
- **Performance for high traffic**:
  - Every list view uses `select_related`/`prefetch_related` to avoid N+1 queries.
  - Database indexes on frequently filtered columns (`SalesData.sale_date`, composite `branch+product+sale_date`, `Product.name/sku`).
  - `CONN_MAX_AGE` persistent DB connections in production.
  - Pagination (25–50 rows) on every list view.
  - WhiteNoise serves compressed, cache-busted static assets directly from the app process — no separate static file infrastructure required to get production-grade static serving.
  - Foreign keys from `SalesData` use `on_delete=PROTECT`, preventing accidental data loss of referenced Products/Branches/Admins; the UI surfaces this as a friendly message instead of a 500 error.

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
Each upload page in the app lists the expected column headers for that entity. Column headers are case-insensitive and whitespace-tolerant. Summary:

| Entity | Required columns |
|---|---|
| Departments | `name`, `code` (optional: `description`) |
| Products | `name`, `sku`, and a department reference — `department_code` and/or `department_name` (creates the department if it doesn't exist yet) (optional: `category`, `description`, `unit_price`) |
| Branches | `name`, `code` (optional: `city`, `state`, `address`) |
| Store Admins | `email` (must be an existing user), optional `phone`, `branch_codes` (comma-separated) |
| Buyers | `name` (optional: `company`, `email`, `phone`, `address`, `product_skus` comma-separated) |
| Sales Data | `product_sku`, `product_name`, `branch_code`, `branch_name`, `admin_email`, `buyer_name`, `quantity`, `value`, `total_stock`; optional `unit_price` (used only if the product doesn't exist yet), `department_code`/`department_name` (optional — falls back to the product's own department if omitted, required only when the row also creates a brand-new product). **`start_date`/`end_date` are not columns** — see below. |

#### Sales Data: the reporting period banner
Rather than a per-row date column, Sales Data spreadsheets carry a single reporting period for the whole file, written as a line **above** the header row:

```
Report Period From :- 01-09-2025,  To :- 30-09-2025
```

On upload, every row before your configured **Header Row** is scanned for this pattern (case-insensitive, tolerant of spacing) and the dates are parsed as `DD-MM-YYYY`. The resulting `start_date`/`end_date` are applied to every Sales Data record created from that file. If no matching line is found above the header row, the whole upload is rejected up front with a clear error before any rows are processed — so set **Header Row** (below) to the row your real column headers are on, keeping the banner line somewhere above it.

#### Custom sheet layout (header row / data start row / start column)
Real-world spreadsheets often don't start their table in cell A1 - there might be a title banner, a couple of blank/notes rows, or a leading "S.No." index column before the actual data. Every upload page has a collapsible **"Sheet Layout Options"** panel (auto-expanded if you submit invalid values) with three settings, all optional and defaulting to the common case:

| Setting | Default | Purpose |
|---|---|---|
| **Header Row** | `1` | The row number containing your column headers. For Sales Data, this must be below the reporting-period banner line (see above). |
| **Data Start Row** | Header Row + 1 | The row number where data begins. Leave blank to use the row immediately after the header row. |
| **Start Column** | `A` | The column letter where your headers/data begin. Anything to the left of this column (e.g. a serial-number column) is ignored. |

Example: a file with a title in row 1, a blank row 2, real headers in row 3, and an extra "S.No." column in column A (so your actual headers start in column B) would use **Header Row = 3**, **Data Start Row = 4**, **Start Column = B**.

These settings are validated server-side (e.g. Data Start Row must come after Header Row, Start Column must be a real column letter) and apply uniformly to every module's upload, since they're implemented once in `apps/core/utils.iter_excel_rows` and `apps/core/forms.ExcelUploadForm` and reused everywhere.

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

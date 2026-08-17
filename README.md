# Sales Tracker

A Django + Bootstrap 5 + HTMX + django-tables2 web application for tracking
product sales across multiple store branches, with fast, chunked Excel
bulk-import support built on pandas + the `calamine` engine.

---

## 1. Features

### Modules
| Module | Fields | Description |
|---|---|---|
| **Users** | — | Built-in `django.contrib.auth.models.User`. Authentication is by **email + password** (username is auto-derived from email and never shown in any form). User creation and password resets happen **only** through the Django admin panel (`/admin/`). |
| **Branches** | Name | Physical store locations. |
| **Products** | Product Code, Description, Department, Admin, Buyer | Sellable products. Department is a plain text field (not a separate module). Admin and Buyer are Users, matched throughout by full name. |
| **Sales Data** | Product, Branch, Start Date, End Date, Total Sales Qty, Total Sales Amt, Total Stock | The core transactional table - one record per product/branch/reporting-period, uniquely identified by (Product, Branch, Start Date, End Date). Includes a **branch-wise aggregated report** in addition to the raw record list. |

### Cross-cutting functionality
- **Excel bulk upload** (`.xlsx`) on Products, Branches, and Sales Data, reachable from each list page, built entirely on **pandas + the `calamine` engine** (a fast Rust-based reader) for large files (500k+ rows):
  - The workbook is read **once** into a DataFrame; header detection, whitespace stripping, and blank-row removal are all **vectorized pandas operations**, not a per-row Python loop.
  - The cleaned DataFrame is split into fixed-size **chunks** (5,000 rows by default) and each chunk is written with a small, constant number of queries via `bulk_create` - independent of file size - rather than one query per row.
  - Bad rows are reported in aggregate (e.g. "12 row(s) skipped - missing 'Product Code' value") rather than one message per row, since vectorized validation naturally works on whole columns at once; the rest of the file keeps processing.
  - Every upload supports a configurable **Header Row / Start Column** (see §4) for spreadsheets that don't start their table in cell A1.
  - **Postgres-optimized writes**: Branches use `bulk_create(..., ignore_conflicts=True)` per chunk - a native `INSERT ... ON CONFLICT DO NOTHING` - to skip rows that already exist. **Products** and **Sales Data** use `bulk_create(..., update_conflicts=True, unique_fields=[...])` - a native `INSERT ... ON CONFLICT (...) DO UPDATE` - to create-or-replace in a single statement. All patterns work identically on PostgreSQL and SQLite.
  - **Master data must exist first**: Products and Branches referenced by a Sales Data upload are looked up, not auto-created - upload them via their own pages first. Admin/Buyer referenced by a Product upload must already exist as Users too.
  - **Sales Data uses a "wide"/pivot source format** (one row per product, one 3-column block per branch) rather than one row per product+branch - see §4 for the full breakdown, confirmed against a real sample export.
- **Live search on every list page**, powered by **HTMX** (no page reload, no custom JavaScript per page) - just a plain search box, no separate search button: typing debounces for 400ms then re-fetches just the results. Tables (rendered by **django-tables2**) get sortable column headers and pagination for free, and both are HTMX-boosted in place too - clicking a column header or a page link never triggers a full page reload. The server-side view code needs no special HTMX-awareness for this: HTMX is configured to request the same page and extract just the results fragment (`hx-select`), so plain-Django full-page loads work identically for JS-disabled clients or direct links.
- **Permissions**: 100% built-in `django.contrib.auth` permissions (`Permission`, `Group`). No custom permission system. A `seed_groups` management command creates three ready-to-use groups (Viewer / Branch Manager / Data Administrator) — see §6.
- **Filters**: Sales Data (both the raw list and the branch-wise report) can be filtered by Branch, Product, and reporting-period date range.
- **Dashboard**: KPIs (total quantity, total value, active product/branch counts), top branches by value, and an interactive, client-side-filterable recent sales table.
- **Responsive Bootstrap 5 UI**: collapsible sidebar on mobile; on desktop the sidebar is pinned under the topbar and only scrolls internally if its own contents overflow, independent of the page's scroll position. Topbar shows app name + logged-in user's full name + logout.
- **Delete confirmation modals**: every delete action is confirmed via a Bootstrap modal before the (POST-only) delete request is sent - works correctly even after an HTMX table swap, since the modal wiring uses event delegation rather than per-button listeners.
- **Double-submit protection**: all form submit buttons are automatically disabled (with a spinner) on submit via shared JS, no per-form wiring needed.
- **Django admin panel**: every model is registered with sensible `list_display`/`list_filter`/`search_fields` and bulk actions (activate/deactivate).

---

## 2. Architecture & tech choices

- **Django 5.2**, Python 3.14+ compatible, class-based views throughout (`ListView` + `django_tables2.SingleTableMixin`, `CreateView`, `UpdateView`, generic `View` for delete, `FormView` for Excel upload).
- **Frontend**: Bootstrap 5 + [HTMX](https://htmx.org) + [django-tables2](https://django-tables2.readthedocs.io) (all loaded from CDN / pip, no JS build step).
  - `apps/core/tables.py` — `BaseTable`, a small shared base every table extends: accepts a `request` kwarg so `render_*` methods can permission-check, and provides `action_buttons()` for consistent Edit/Delete markup. Edit links carry `hx-boost="false"` so they navigate normally even though their containing table is HTMX-boosted for sort/page links.
  - Each list template wraps its `{% render_table table %}` in a `<div id="results" hx-boost="true" hx-target="#results" hx-select="#results" hx-swap="outerHTML">` - this alone makes every sort/page link inside act like an HTMX partial update, with zero django-tables2-specific HTMX code.
- **App layout**: one Django app per module under `apps/`, plus `apps/core` for shared, reusable building blocks:
  - `apps/core/mixins.py` — `CrudPermissionMixin` (login + built-in permission check), `ExcelUploadView` (generic batched bulk-import base class - see below), `ObjectDeleteView` (generic POST-only delete with `ProtectedError` handling), `SuccessMessageMixin`.
  - `apps/core/forms.py` — `BootstrapModelForm` (auto-applies Bootstrap CSS classes to every field), `ExcelUploadForm`.
  - `apps/core/utils.py` — Excel reading built on **pandas + the `calamine` engine** (`python-calamine`) rather than openpyxl. `load_excel()` reads the sheet once; `build_data_frame()` slices out a standard single-header-row/data region; `chunk_dataframe()` yields fixed-size slices for batched writes; `extract_pre_header_row_texts()` joins each pre-header row's cells into one string (robust to banner text split across adjacent cells) for regex-based banner parsing; `normalize_text()` collapses all whitespace including non-breaking spaces (`\xa0`, seen in the real sample export) to single regular spaces.
  - `apps/core/models.py` — `TimeStampedModel` abstract base (`created_at`, `updated_at`, `is_active`) inherited by every entity.
- **Excel upload architecture** (`apps/core/mixins.ExcelUploadView`): built for files with 500k+ rows and entirely DataFrame-native.
  - `build_dataframe(raw_df, header_row, start_col)` (overridable per view) turns the raw sheet into a clean, long DataFrame - one row per record. The default delegates to `apps.core.utils.build_data_frame` (the common single-header-row case); **Sales Data overrides this entirely** to unpivot its wide/pivot source format - see §4.
  - `process_chunk(chunk_df)` (required per view): given a DataFrame slice of up to `chunk_size` rows, validates/resolves/writes that chunk - typically vectorized pandas cleaning followed by a single `bulk_create` - and returns `(created, updated, skipped, errors)`.
  - The base view loads the workbook once, builds the DataFrame, chunks it, and calls `process_chunk` per chunk; a chunk that fails outright is caught and reported without aborting the rest of the file.
- **Settings are split** (`config/settings/base.py`, `development.py`, `production.py`) so environment-specific behaviour never has to be toggled by hand — set `DJANGO_SETTINGS_MODULE` (the provided scripts do this for you) and everything follows.
- **Logging**: development logs to console at `DEBUG` level; production adds rotating file handlers (`logs/sales_tracker.log`, 10MB × 10 backups, plus a separate error-only log) alongside console output.
- **Performance for high traffic**:
  - Every list view uses `select_related` to avoid N+1 queries.
  - Database indexes on frequently filtered columns (`SalesData.start_date`/`end_date`, composite `branch+product+start_date`), plus a `UniqueConstraint` on `SalesData(product, branch, start_date, end_date)` that both enforces the one-record-per-period rule and backs the Postgres `ON CONFLICT` upsert used by the Sales Data upload.
  - `CONN_MAX_AGE` persistent DB connections in production.
  - django-tables2's built-in pagination on every list view; HTMX makes sorting/paging/searching feel instant without a full page reload.
  - WhiteNoise serves compressed, cache-busted static assets directly from the app process.
  - Foreign keys from `SalesData`/`Product` use `on_delete=PROTECT`; the UI surfaces a friendly message instead of a 500 error when a delete would violate that.
  - Excel uploads: chunked, vectorized bulk writes. Validated in development against a real ~2,300-cell wide-format sales report (100 products × 23 branches) and synthetic files up to 20k unpivoted rows at ~3,800 rows/sec - a 500k-row file completes in a couple of minutes.

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
│   ├── core/            # shared mixins, forms, tables, models, middleware, management commands
│   ├── accounts/        # email auth backend, login/logout views, User admin customization
│   ├── products/
│   ├── branches/
│   ├── sales_data/
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

Want a handful of test users quickly? `python manage.py create_dev_users "Alice Admin" "Bob Manager"` - see §5.

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
User creation and password resets are **admin-panel only** by design. Go to `/admin/`, add a user under **Accounts > Users** with an email, first/last name and password — the username field is hidden and populated automatically. Assign them to a permission Group (see §6) or set individual permissions. (For local dev only, `create_dev_users` - see §5 - can create several at once from full names.)

### Excel upload formats

#### Branches
One column: `Branch`. A row referencing a branch that already exists is skipped (not duplicated).

#### Products
Columns: `Product Code`, `Description`, `Department`, `Admin`, `Buyer`. **Admin** and **Buyer** are matched by the User's **full name** (first name + last name), treated as a unique identifier - the User must already exist (create via `/admin/` or `create_dev_users` in dev). A row for a Product Code that already exists **updates** that product (description/department/admin/buyer); a new Product Code is created - single-statement upsert, not skip-if-exists.

#### Sales Data - wide/pivot format (confirmed against a real sample export)
Unlike the other uploads, a Sales Data spreadsheet is **not** one row per record. It's a wide report - one row per **product**, with each **branch's** figures in their own 3-column block, e.g.:

```
                                    Report Period From :- 01-09-2025,  To :- 30-09-2025

                            Total                    ACORNHOEK                BOARDS WR
Sl.No  Prod Code  Description  Department  Sales Qty  Sales Amt  Stock  Sales Qty  Sales Amount  Stock  Sales Qty ...
1      ABC123     Widget        Hardware      42        999.50    10       5          119.90       2       0    ...
```

- The **reporting period** (`Report Period From :- 01-09-2025,  To :- 30-09-2025`) sits on its own line somewhere above the header row. It may be **split across several adjacent cells on that same row** due to source-file formatting - the parser joins every non-empty cell in a row together before pattern-matching, so this is handled automatically; you don't need to fix the source file.
- The **branch name** for each 3-column block (e.g. "ACORNHOEK") sits in the row **directly above** the header row, positioned above that block's "Sales Qty" column. A "Total" block (aggregating across all branches) is present too and is automatically ignored - only named-branch blocks are read.
- Set **Header Row** (Sheet Layout Options, below) to the row containing `Prod Code` / `Sales Qty` / etc. - in the confirmed sample file, that's **row 7** (title on row 2, report period on row 4, branch names on row 6, headers on row 7).
- Only `Prod Code` plus each block's `Sales Qty` / `Sales Amount` / `Stock` are read - `Description`/`Department` live on the Product record itself now, not on Sales Data, so they aren't re-read here.
- **Product Code** and **Branch** must already exist (upload Products and Branches first) - unknown references are reported and that row is skipped, not auto-created.
- Quantities and amounts are **signed** (not required to be positive) - the real sample data includes negative values representing returns/adjustments.
- For a given **Product + Branch** within this file's reporting period, uploading again **replaces** the existing record's quantity/amount/stock; a different period (or a first-time product/branch combination) creates a new record. This is enforced by a database `UniqueConstraint` on `(product, branch, start_date, end_date)` and implemented as a single `bulk_create(update_conflicts=True, unique_fields=[...])` call per chunk.

#### Custom sheet layout (header row / start column)
Every upload page has a collapsible **"Sheet Layout Options"** panel (auto-expanded if you submit invalid values) with two settings:

| Setting | Default | Purpose |
|---|---|---|
| **Header Row** | `1` | The row number containing your column headers. For Sales Data, this is the row with `Prod Code`/`Sales Qty` - see above (branch names/report period are found automatically relative to it). |
| **Start Column** | `A` | The column letter where your headers/data begin. Anything to the left is ignored (e.g. a leading serial-number column). |

These settings are validated server-side and, for the standard (non-Sales-Data) uploads, are implemented once in `apps/core/utils`/`apps/core/forms.ExcelUploadForm` and reused everywhere.

---

## 5. Helper scripts (`scripts/`) & dev management commands

| Script | Purpose |
|---|---|
| `setup.sh` | One-time bootstrap: venv, dependencies, `.env`, initial migration. |
| `run_dev.sh [host:port]` | Runs the dev server with `config.settings.development` (defaults to `127.0.0.1:8000`). |
| `run_prod.sh` | Runs the app under Gunicorn with `config.settings.production`. Reads `BIND_ADDR`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT` from the environment if set. |
| `migrate.sh [dev\|prod]` | Runs `makemigrations` + `migrate` against the chosen environment. |
| `createsuperuser.sh` | Interactive superuser creation (email/password only). |
| `collectstatic.sh` | Collects static files into `staticfiles/` for production (WhiteNoise). |
| `backup_db.sh` | Dumps all application data to a timestamped JSON fixture under `backups/` (database-agnostic; use `pg_dump` for full-fidelity Postgres backups in production). |
| `reset_migrations.sh [app...] [--keep-db]` | **Dev only.** Deletes migration files for the given app(s) (or every app, if none given) and regenerates a fresh `0001_initial`, dropping `db.sqlite3` unless `--keep-db` is passed. Resetting a single app whose models other apps reference via ForeignKey will break the migration graph unless you reset those apps together too - the script warns about this; when in doubt, omit arguments to reset everything (always safe). |

All scripts are POSIX shell, executable, and safe to re-run.

### `create_dev_users` (management command, dev only)

Creates Users from a list of full names, purely for local development - it refuses to run unless `DEBUG=True`. Emails are generated from the name (`"Alice Admin"` → `alice.admin@example.com`) and every created user shares one password.

```bash
python manage.py create_dev_users "Alice Admin" "Bob Manager"
python manage.py create_dev_users --file names.txt                      # one full name per line
python manage.py create_dev_users "Alice Admin" --password "MyPass123!" --domain example.org
python manage.py create_dev_users "Alice Admin" --staff                 # or --superuser
```

Default password if `--password` isn't given: `DevPass123!` (printed at the end of the run as a reminder). Names that would collide with an existing user's email are skipped, not overwritten.

---

## 6. Permissions model

The app uses Django's built-in permission framework exclusively — no custom roles table.

- Every model automatically gets `add_`, `change_`, `delete_`, `view_` permissions (Django default).
- Views check permissions via `PermissionRequiredMixin` (wrapped as `CrudPermissionMixin` in `apps/core/mixins.py`), e.g. a Products list view requires `products.view_product`. Table Edit/Delete action buttons are only rendered for users who hold the corresponding permission (checked via `request` passed into the table - see §2).
- The sidebar only shows links to modules the logged-in user actually has `view_*` permission for.
- `python manage.py seed_groups` creates three starter groups:
  - **Viewer** — view-only across all modules.
  - **Branch Manager** — view everything, plus add/edit Sales Data.
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

This project was validated end-to-end during development using Django's test client, including against the **real confirmed sample Sales Data export**: migrations apply cleanly from scratch; email login and the auto-derived-username signal work correctly; every list/add/upload page returns HTTP 200 for an authenticated user; permission checks correctly redirect users lacking the required permission; Product/Branch/Sales Data CRUD works; django-tables2 sorting and pagination work; the search-icon-free HTMX search bars filter correctly; Product Excel upload correctly resolves Admin/Buyer by full name and creates-or-updates; the real 100-product × 23-branch wide-format Sales Data file uploads correctly (126 sparse records, including negative quantities/amounts for returns), and re-uploading the same file replaces those 126 records rather than duplicating them; and attempting to delete a Branch/Department still referenced elsewhere surfaces a friendly error instead of a server crash.

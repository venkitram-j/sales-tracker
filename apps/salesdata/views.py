import logging

import pandas as pd
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView

from apps.branches.models import Branch
from apps.buyers.models import Buyer
from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin
from apps.core.utils import extract_pre_header_text
from apps.departments.models import Department
from apps.products.models import Product
from apps.store_admins.models import StoreAdmin

from .forms import SalesDataForm
from .models import SalesData
from .report_period import parse_branch_name, parse_report_period

logger = logging.getLogger("apps.salesdata")
User = get_user_model()


class SalesDataFilterMixin:
    """Shared query-param filtering used by both the raw list and the branch-wise report."""

    def filter_queryset(self, qs):
        request = self.request
        branch_id = request.GET.get("branch")
        product_id = request.GET.get("product")
        department_id = request.GET.get("department")
        admin_id = request.GET.get("admin")
        buyer_id = request.GET.get("buyer")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if product_id:
            qs = qs.filter(product_code_id=product_id)
        if department_id:
            qs = qs.filter(department_id=department_id)
        if admin_id:
            qs = qs.filter(admin_id=admin_id)
        if buyer_id:
            qs = qs.filter(buyer_id=buyer_id)
        if date_from:
            qs = qs.filter(start_date__gte=date_from)
        if date_to:
            qs = qs.filter(end_date__lte=date_to)
        return qs

    def get_filter_context(self):
        return {
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "products": Product.objects.filter(is_active=True).order_by("product_code"),
            "departments": Department.objects.filter(is_active=True).order_by("name"),
            "admins": StoreAdmin.objects.select_related("user").filter(is_active=True),
            "buyers": Buyer.objects.filter(is_active=True).order_by("name"),
            "selected_branch": self.request.GET.get("branch", ""),
            "selected_product": self.request.GET.get("product", ""),
            "selected_department": self.request.GET.get("department", ""),
            "selected_admin": self.request.GET.get("admin", ""),
            "selected_buyer": self.request.GET.get("buyer", ""),
            "date_from": self.request.GET.get("date_from", ""),
            "date_to": self.request.GET.get("date_to", ""),
        }


class SalesDataListView(SalesDataFilterMixin, CrudPermissionMixin, ListView):
    """Raw, row-level sales records with full CRUD entry points."""

    model = SalesData
    permission_required = "salesdata.view_salesdata"
    template_name = "salesdata/list.html"
    context_object_name = "sales_records"
    paginate_by = 30

    def get_queryset(self):
        qs = SalesData.objects.select_related("product_code", "branch", "department", "admin__user", "buyer")
        return self.filter_queryset(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.get_filter_context())
        totals = self.get_queryset().aggregate(total_qty=Sum("total_sales_qty"), total_value=Sum("total_sales_amt"))
        ctx["total_qty"] = totals["total_qty"] or 0
        ctx["total_value"] = totals["total_value"] or 0
        return ctx


class SalesDataBranchWiseView(SalesDataFilterMixin, CrudPermissionMixin, ListView):
    """Branch-wise aggregated view: totals per branch + product combination."""

    permission_required = "salesdata.view_salesdata"
    template_name = "salesdata/branch_wise.html"
    context_object_name = "summary_rows"
    paginate_by = 50

    def get_queryset(self):
        qs = SalesData.objects.select_related("product_code", "branch", "department")
        qs = self.filter_queryset(qs)
        return (
            qs.values("branch__name", "product_code__product_code", "product_code__description", "department__name")
            .annotate(
                total_quantity=Sum("total_sales_qty"),
                total_value=Sum("total_sales_amt"),
                total_stock=Sum("total_stock"),
                transaction_count=Count("id"),
            )
            .order_by("branch__name", "product_code__product_code")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.get_filter_context())
        return ctx


class SalesDataCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = SalesData
    form_class = SalesDataForm
    permission_required = "salesdata.add_salesdata"
    template_name = "salesdata/form.html"
    success_url = reverse_lazy("salesdata:list")
    success_message = "Sales record added successfully."


class SalesDataUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = SalesData
    form_class = SalesDataForm
    permission_required = "salesdata.change_salesdata"
    template_name = "salesdata/form.html"
    success_url = reverse_lazy("salesdata:list")
    success_message = "Sales record updated successfully."


class SalesDataDeleteView(ObjectDeleteView):
    model = SalesData
    permission_required = "salesdata.delete_salesdata"
    success_url = reverse_lazy("salesdata:list")
    success_message = "Sales record deleted successfully."


class SalesDataExcelUploadView(ExcelUploadView):
    """Columns expected (case-insensitive, matching the model field names):
    "Product Code", "Description", "Department", "Admin", "Buyer",
    "Total Sales Qty", "Total Sales Amt", "Total Stock".

    Branch and the reporting period (start_date / end_date) are NOT
    per-row columns - the whole file covers a single branch and a single
    period, given as banner lines above the header row:

        Branch :- Downtown
        Report Period From :- 01-09-2025,  To :- 30-09-2025

    NOTE: the exact wording/format of the "Branch" banner line has not
    been confirmed against a real sample file - apps/salesdata/report_period.py
    documents the flexible pattern currently used
    (`Branch[:/- ]<name>`, case-insensitive) and is the single place to
    adjust it once the real format is confirmed.

    Product Code, Department, Buyer and Admin must all already exist
    (upload them via their own pages first) - this view does not
    auto-create master data. Only the Branch referenced in the banner
    must also already exist.

    Upsert semantics: for a given product_code within this upload's
    branch + reporting period, an existing Sales Data record is REPLACED
    (its fields updated) rather than duplicated, using a single
    Postgres-native `INSERT ... ON CONFLICT (...) DO UPDATE` per chunk
    (bulk_create(update_conflicts=True)) - no separate per-row exists
    check.
    """

    permission_required = "salesdata.add_salesdata"
    success_url = reverse_lazy("salesdata:list")
    entity_label = "sales records"
    upload_title = "Bulk Upload Sales Data"
    expected_columns = [
        "Product Code", "Description", "Department", "Admin", "Buyer",
        "Total Sales Qty", "Total Sales Amt", "Total Stock",
    ]
    upload_help_text = (
        "Branch and the reporting period are NOT columns - they're parsed automatically from lines above your "
        "header row, e.g. \"Branch :- Downtown\" and \"Report Period From :- 01-09-2025,  To :- 30-09-2025\". "
        "Set Header Row (below) to the row your table headers are actually on. Product Code, Department, Admin "
        "and Buyer must already exist. An existing record for the same product code within this branch + period "
        "is replaced with the new values; otherwise a new record is created."
    )

    REQUIRED_COLUMNS = {
        "product_code", "description", "department", "admin", "buyer",
        "total_sales_qty", "total_sales_amt", "total_stock",
    }

    def before_rows(self, form, raw_df, header_row):
        texts = extract_pre_header_text(raw_df, header_row)

        start_date, end_date = parse_report_period(texts)
        if not start_date or not end_date:
            raise ValueError(
                "Could not find a 'Report Period From :- DD-MM-YYYY, To :- DD-MM-YYYY' line above the header row. "
                "Make sure Header Row (Sheet Layout Options) is set below that line, and the line itself is somewhere above it."
            )

        branch_name = parse_branch_name(texts)
        if not branch_name:
            raise ValueError(
                "Could not find a 'Branch :- <name>' line above the header row. "
                "Make sure Header Row (Sheet Layout Options) is set below that line."
            )
        try:
            branch = Branch.objects.get(name=branch_name)
        except Branch.DoesNotExist:
            raise ValueError(f"Branch '{branch_name}' does not exist. Upload it via the Branches module first.")

        self._start_date = start_date
        self._end_date = end_date
        self._branch = branch

    def process_chunk(self, chunk_df: pd.DataFrame):
        missing_cols = self.REQUIRED_COLUMNS - set(chunk_df.columns)
        if missing_cols:
            return 0, 0, 0, [f"The uploaded file must have columns: {', '.join(sorted(missing_cols))}."]

        df = chunk_df[list(self.REQUIRED_COLUMNS)].copy()
        for col in ["product_code", "description", "department", "admin", "buyer"]:
            df[col] = df[col].astype(str).str.strip()
        df["admin"] = df["admin"].str.lower()

        for col in ["total_sales_qty", "total_sales_amt", "total_stock"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        errors = []
        invalid_mask = (
            (df["product_code"] == "") | (df["department"] == "") | (df["admin"] == "") | (df["buyer"] == "")
            | df["total_sales_qty"].isna() | (df["total_sales_qty"] <= 0)
            | df["total_sales_amt"].isna() | (df["total_sales_amt"] < 0)
            | df["total_stock"].isna() | (df["total_stock"] < 0)
        )
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            errors.append(
                f"{invalid_count} row(s) skipped - missing 'Product Code'/'Department'/'Admin'/'Buyer', or an "
                "invalid/non-positive 'Total Sales Qty'/'Total Sales Amt'/'Total Stock'."
            )
        df = df[~invalid_mask]

        if df.empty:
            return 0, 0, 0, errors

        # De-duplicate within this chunk, keeping the last occurrence of a product_code
        # (branch + period are constant for the whole file, so product_code alone is the chunk key).
        df = df.drop_duplicates(subset="product_code", keep="last")

        # --- Resolve references; all must already exist -------------------
        product_codes = set(df["product_code"].unique())
        product_map = {p.product_code: p for p in Product.objects.filter(product_code__in=product_codes)}
        missing_products = sorted(product_codes - set(product_map.keys()))
        if missing_products:
            errors.append(f"Unknown product code(s), row(s) skipped: {', '.join(missing_products)}.")
            df = df[df["product_code"].isin(product_map.keys())]

        dept_names = set(df["department"].unique()) if not df.empty else set()
        dept_map = {d.name: d for d in Department.objects.filter(name__in=dept_names)}
        missing_depts = sorted(dept_names - set(dept_map.keys()))
        if missing_depts:
            errors.append(f"Unknown department(s), row(s) skipped: {', '.join(missing_depts)}.")
            df = df[df["department"].isin(dept_map.keys())]

        buyer_names = set(df["buyer"].unique()) if not df.empty else set()
        buyer_map = {b.name: b for b in Buyer.objects.filter(name__in=buyer_names)}
        missing_buyers = sorted(buyer_names - set(buyer_map.keys()))
        if missing_buyers:
            errors.append(f"Unknown buyer(s), row(s) skipped: {', '.join(missing_buyers)}.")
            df = df[df["buyer"].isin(buyer_map.keys())]

        admin_emails = set(df["admin"].unique()) if not df.empty else set()
        user_map = {u.email.lower(): u for u in User.objects.filter(email__in=admin_emails)}
        missing_users = sorted(admin_emails - set(user_map.keys()))
        if missing_users:
            errors.append(f"No user found for admin email(s): {', '.join(missing_users)}.")

        admin_map = {}
        if user_map:
            user_ids = [u.id for u in user_map.values()]
            store_admins = StoreAdmin.objects.filter(user_id__in=user_ids).select_related("user")
            admin_map = {sa.user.email.lower(): sa for sa in store_admins}
            missing_store_admins = sorted(set(user_map.keys()) - set(admin_map.keys()))
            if missing_store_admins:
                errors.append(
                    f"User(s) found but not registered as Store Admins, row(s) skipped: "
                    f"{', '.join(missing_store_admins)}. Add them via the Admins module first."
                )
        if not df.empty:
            df = df[df["admin"].isin(admin_map.keys())]

        if df.empty:
            return 0, 0, 0, errors

        rows = list(df.itertuples(index=False))
        codes_in_chunk = [r.product_code for r in rows]

        existing_before = set(
            SalesData.objects.filter(
                branch=self._branch, start_date=self._start_date, end_date=self._end_date,
                product_code__product_code__in=codes_in_chunk,
            ).values_list("product_code__product_code", flat=True)
        )

        objs = [
            SalesData(
                product_code=product_map[r.product_code],
                description=r.description,
                department=dept_map[r.department],
                branch=self._branch,
                admin=admin_map[r.admin],
                buyer=buyer_map[r.buyer],
                start_date=self._start_date,
                end_date=self._end_date,
                total_sales_qty=int(r.total_sales_qty),
                total_sales_amt=r.total_sales_amt,
                total_stock=int(r.total_stock),
            )
            for r in rows
        ]

        SalesData.objects.bulk_create(
            objs,
            update_conflicts=True,
            update_fields=[
                "description", "department", "admin", "buyer",
                "total_sales_qty", "total_sales_amt", "total_stock",
            ],
            unique_fields=["product_code", "branch", "start_date", "end_date"],
            batch_size=self.chunk_size,
        )

        updated = len(existing_before)
        created = len(objs) - updated
        return created, updated, 0, errors

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView

from apps.branches.models import Branch
from apps.buyers.models import Buyer
from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin
from apps.core.utils import scan_text_before_row
from apps.departments.models import Department
from apps.products.models import Product
from apps.store_admins.models import StoreAdmin

from .forms import SalesDataForm
from .models import SalesData
from .report_period import parse_report_period

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
            qs = qs.filter(product_id=product_id)
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
            "products": Product.objects.filter(is_active=True).order_by("name"),
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
        qs = SalesData.objects.select_related("product", "branch", "department", "admin__user", "buyer")
        return self.filter_queryset(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.get_filter_context())
        totals = self.get_queryset().aggregate(total_qty=Sum("sales_quantity"), total_value=Sum("sales_value"))
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
        qs = SalesData.objects.select_related("product", "branch", "department")
        qs = self.filter_queryset(qs)
        return (
            qs.values("branch__name", "branch__code", "product__name", "product__sku", "department__name")
            .annotate(
                total_quantity=Sum("sales_quantity"),
                total_value=Sum("sales_value"),
                total_stock=Sum("total_stock"),
                transaction_count=Count("id"),
            )
            .order_by("branch__name", "product__name")
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
    """Bulk-imports sales/stock-period records, auto-creating Product /
    Branch / Department / StoreAdmin / Buyer records as needed so a single
    spreadsheet can seed the whole dataset.

    Expected per-row columns (case-insensitive):
        product_sku, product_name, unit_price (optional, only used if the
        product doesn't exist yet), department_code, department_name
        (optional - falls back to the product's existing department if
        omitted), branch_code, branch_name, admin_email, buyer_name,
        quantity, value, total_stock

    The reporting period (start_date / end_date) is NOT a per-row column.
    It is parsed once from a banner line that sits above the header row,
    in the format:

        Report Period From :- 01-09-2025,  To :- 30-09-2025

    and applied to every row created from this upload. Set "Header Row"
    (in Sheet Layout Options) to the row your real column headers are on
    so the banner - which sits above it - gets picked up.
    """

    permission_required = "salesdata.add_salesdata"
    success_url = reverse_lazy("salesdata:list")
    entity_label = "sales records"
    upload_title = "Bulk Upload Sales Data"
    expected_columns = [
        "product_sku", "product_name", "unit_price (optional)",
        "department_code (optional)", "department_name (optional)",
        "branch_code", "branch_name", "admin_email", "buyer_name",
        "quantity", "value", "total_stock",
    ]
    upload_help_text = (
        "start_date / end_date are NOT columns in the table - they're parsed automatically from a line "
        "above your header row reading: \"Report Period From :- 01-09-2025,  To :- 30-09-2025\". "
        "Set Header Row (below) to the row your table headers are actually on, so that line is included in the scan."
    )

    def before_rows(self, form, uploaded_file, header_row):
        texts = scan_text_before_row(uploaded_file, header_row)
        start_date, end_date = parse_report_period(texts)
        if not start_date or not end_date:
            raise ValueError(
                "Could not find a 'Report Period From :- DD-MM-YYYY, To :- DD-MM-YYYY' line above the header row. "
                "Make sure Header Row (Sheet Layout Options) is set below that line, and the line itself is somewhere above it."
            )
        self._start_date = start_date
        self._end_date = end_date

    def process_row(self, row_number, row):
        product_sku = (row.get("product_sku") or "").strip()
        product_name = (row.get("product_name") or "").strip()
        branch_code = (row.get("branch_code") or "").strip()
        branch_name = (row.get("branch_name") or "").strip()
        admin_email = (row.get("admin_email") or "").strip().lower()
        buyer_name = (row.get("buyer_name") or "").strip()

        if not (product_sku and product_name and branch_code and branch_name and admin_email and buyer_name):
            raise ValueError(
                "'product_sku', 'product_name', 'branch_code', 'branch_name', 'admin_email' and 'buyer_name' are all required."
            )

        quantity_raw = row.get("quantity")
        value_raw = row.get("value")
        total_stock_raw = row.get("total_stock")
        try:
            quantity = int(quantity_raw)
            if quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("'quantity' must be a positive whole number.")

        try:
            value = Decimal(str(value_raw))
        except (InvalidOperation, TypeError):
            raise ValueError("'value' must be numeric.")

        try:
            total_stock = int(total_stock_raw)
            if total_stock < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("'total_stock' must be a whole number.")

        # --- get-or-create supporting records -----------------------------
        department_from_row = self._resolve_department(row)

        unit_price_raw = row.get("unit_price")
        try:
            unit_price = Decimal(str(unit_price_raw)) if unit_price_raw not in (None, "") else (value / quantity)
        except (InvalidOperation, ZeroDivisionError):
            unit_price = Decimal("0")

        existing_product = Product.objects.filter(sku=product_sku).select_related("department").first()
        if existing_product:
            product = existing_product
            department = department_from_row or existing_product.department
        else:
            if department_from_row is None:
                raise ValueError(
                    f"Product '{product_sku}' does not exist yet - 'department_code' or 'department_name' "
                    "is required to create it."
                )
            department = department_from_row
            product = Product.objects.create(
                sku=product_sku, name=product_name, unit_price=unit_price, department=department
            )

        branch, _ = Branch.objects.get_or_create(
            code=branch_code,
            defaults={"name": branch_name},
        )
        try:
            user = User.objects.get(email__iexact=admin_email)
        except User.DoesNotExist:
            raise ValueError(f"No user found with email '{admin_email}'. Create the user in the admin panel first.")

        admin, _ = StoreAdmin.objects.get_or_create(user=user)
        if not admin.branches.filter(pk=branch.pk).exists():
            admin.branches.add(branch)

        buyer, _ = Buyer.objects.get_or_create(name=buyer_name)

        SalesData.objects.create(
            product=product,
            branch=branch,
            department=department,
            admin=admin,
            buyer=buyer,
            sales_quantity=quantity,
            sales_value=value,
            total_stock=total_stock,
            start_date=self._start_date,
            end_date=self._end_date,
        )

    @staticmethod
    def _resolve_department(row):
        """Uses the row's department_code/department_name if given (creating it
        if needed); otherwise returns None so the caller falls back to the
        product's own department.
        """
        dept_code = (row.get("department_code") or "").strip()
        dept_name = (row.get("department_name") or "").strip()
        if not dept_code and not dept_name:
            return None
        if dept_code:
            department, _ = Department.objects.get_or_create(
                code=dept_code, defaults={"name": dept_name or dept_code}
            )
        else:
            department, _ = Department.objects.get_or_create(
                name=dept_name, defaults={"code": dept_name[:32]}
            )
        return department

import logging

import pandas as pd
from django.db.models import Sum, Count
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView

from apps.branches.models import Branch
from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, FilteredTableListView, ObjectDeleteView, SuccessMessageMixin
from apps.core.utils import ExcelParseError, extract_pre_header_row_texts, normalize_text
from apps.products.models import Product

from .filters import SalesDataFilter
from .forms import SalesDataForm
from .models import SalesData
from .report_period import parse_report_period
from .tables import SalesDataBranchWiseTable, SalesDataTable

logger = logging.getLogger("apps.sales_data")


class SalesDataListView(FilteredTableListView):
    """Raw, row-level sales records with full CRUD entry points."""

    model = SalesData
    permission_required = "sales_data.view_salesdata"
    template_name = "sales_data/list.html"
    table_class = SalesDataTable
    filterset_class = SalesDataFilter

    def get_base_queryset(self):
        return SalesData.objects.select_related("product", "branch")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        totals = self.filterset.qs.aggregate(total_qty=Sum("total_sales_qty"), total_value=Sum("total_sales_amt"))
        ctx["total_qty"] = totals["total_qty"] or 0
        ctx["total_value"] = totals["total_value"] or 0
        return ctx


class SalesDataBranchWiseView(FilteredTableListView):
    """Branch-wise aggregated view: totals per branch + product combination."""

    model = SalesData
    permission_required = "sales_data.view_salesdata"
    template_name = "sales_data/branch_wise.html"
    table_class = SalesDataBranchWiseTable
    filterset_class = SalesDataFilter

    def get_base_queryset(self):
        return SalesData.objects.select_related("product", "branch")

    def get_table_data(self):
        rows = (
            self.filterset.qs.values("branch__name", "product__product_code", "product__description")
            .annotate(
                total_quantity=Sum("total_sales_qty"),
                total_value=Sum("total_sales_amt"),
                total_stock=Sum("total_stock"),
                transaction_count=Count("id"),
            )
            .order_by("branch__name", "product__product_code")
        )
        return [
            {
                "branch": row["branch__name"],
                "product_code": row["product__product_code"],
                "description": row["product__description"],
                "transaction_count": row["transaction_count"],
                "total_quantity": row["total_quantity"],
                "total_value": row["total_value"],
                "total_stock": row["total_stock"],
            }
            for row in rows
        ]


class SalesDataCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = SalesData
    form_class = SalesDataForm
    permission_required = "sales_data.add_salesdata"
    template_name = "sales_data/form.html"
    success_url = reverse_lazy("sales_data:list")
    success_message = "Sales record added successfully."


class SalesDataUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = SalesData
    form_class = SalesDataForm
    permission_required = "sales_data.change_salesdata"
    template_name = "sales_data/form.html"
    success_url = reverse_lazy("sales_data:list")
    success_message = "Sales record updated successfully."


class SalesDataDeleteView(ObjectDeleteView):
    model = SalesData
    permission_required = "sales_data.delete_salesdata"
    success_url = reverse_lazy("sales_data:list")
    success_message = "Sales record deleted successfully."


class SalesDataExcelUploadView(ExcelUploadView):
    """Reads a "wide"/pivot-format itemwise sales report: one row per
    product, with each branch's Sales Qty / Sales Amount / Stock in its
    own 3-column block (plus a "Total" block that's ignored). Column
    layout (matching the confirmed sample file):

        Sl.No | Prod Code | Description | Department | (blank) |
        Total Sales Qty | Total Sales Amt | Total Stock |
        Sales Qty | Sales Amount | Stock  <- repeated once per branch

    The branch name for each 3-column block sits directly above the
    header row (e.g. "ACORNHOEK" above the first block's "Sales Qty"
    header). The reporting period is parsed once from a banner line
    further above that - possibly split across several adjacent cells on
    the same row - reading:

        Report Period From :- 01-09-2025,  To :- 30-09-2025

    Only Product Code and the three sales figures are used per branch
    block ("Description"/"Department" live on the Product record itself
    now, not on Sales Data). Product Code must already exist (upload
    Products first); Branch must also already exist (upload Branches
    first) - unknown references are reported and skipped rather than
    auto-created.

    Upsert semantics: for a given Product + Branch within this upload's
    reporting period, an existing Sales Data record is REPLACED (its
    quantities/amount/stock updated) rather than duplicated, using a
    single Postgres-native `INSERT ... ON CONFLICT (...) DO UPDATE` per
    chunk (bulk_create(update_conflicts=True)).
    """

    permission_required = "sales_data.add_salesdata"
    success_url = reverse_lazy("sales_data:list")
    entity_label = "sales records"
    upload_title = "Bulk Upload Sales Data"
    expected_columns = [
        "Prod Code", "... (Description/Department are read but not stored on Sales Data)",
        "Sales Qty / Sales Amount / Stock - repeated once per branch, with the branch name directly above the header row",
    ]
    upload_help_text = (
        "This is a wide/pivot report: one row per product, with each branch's Sales Qty / Sales Amount / Stock "
        "in its own 3-column block, and the branch name in the row directly above the header row. Set Header Row "
        "to the row containing 'Prod Code' / 'Sales Qty' etc (for the confirmed sample file, that's row 7). "
        "The reporting period is parsed automatically from a \"Report Period From :- 01-09-2025,  To :- 30-09-2025\" "
        "line further above. Product Code and Branch must already exist. An existing record for the same product + "
        "branch within this period is replaced with the new values; otherwise a new record is created."
    )

    def before_rows(self, form, raw_df: pd.DataFrame, header_row):
        texts = extract_pre_header_row_texts(raw_df, header_row)
        start_date, end_date = parse_report_period(texts)
        if not start_date or not end_date:
            raise ValueError(
                "Could not find a 'Report Period From :- DD-MM-YYYY, To :- DD-MM-YYYY' line above the header row. "
                "Make sure Header Row (Sheet Layout Options) is set below that line."
            )
        self._start_date = start_date
        self._end_date = end_date

    def build_dataframe(self, raw_df: pd.DataFrame, header_row, start_col):
        header_idx = header_row - 1
        branch_row_idx = header_idx - 1
        col_start_idx = start_col - 1
        ncols = raw_df.shape[1]

        if branch_row_idx < 0:
            raise ExcelParseError(
                "Header Row must be at least 2, since the branch names sit on the row directly above it."
            )
        if header_idx >= len(raw_df) or col_start_idx >= ncols:
            raise ExcelParseError(f"Header row {header_row} was not found in the uploaded file.")

        header_values = raw_df.iloc[header_idx]
        branch_row_values = raw_df.iloc[branch_row_idx]

        def norm(v):
            return normalize_text(v).lower()

        product_col = None
        for col in range(col_start_idx, ncols):
            if norm(header_values.iloc[col]) in ("prod code", "product code"):
                product_col = col
                break
        if product_col is None:
            raise ExcelParseError(
                f"Could not find a 'Prod Code' column in header row {header_row}. Check the Header Row setting."
            )

        # Each branch's block: a "Sales Qty" header with a non-blank, non-"Total"
        # branch name directly above it, followed by matching Sales Amount/Stock columns.
        branch_blocks = []
        for col in range(col_start_idx, ncols):
            if norm(header_values.iloc[col]) != "sales qty":
                continue
            branch_name = normalize_text(branch_row_values.iloc[col])
            if not branch_name or branch_name.lower() == "total":
                continue
            amt_col, stock_col = col + 1, col + 2
            amt_ok = amt_col < ncols and norm(header_values.iloc[amt_col]) in ("sales amount", "sales amt")
            stock_ok = stock_col < ncols and norm(header_values.iloc[stock_col]) == "stock"
            if amt_ok and stock_ok:
                branch_blocks.append((branch_name, col, amt_col, stock_col))

        if not branch_blocks:
            raise ExcelParseError(
                "Could not find any branch sales columns (expected a 'Sales Qty' / 'Sales Amount' / 'Stock' "
                "column triplet per branch, with the branch name directly above the header row)."
            )

        data_start = header_idx + 1
        frames = []
        for branch_name, qty_col, amt_col, stock_col in branch_blocks:
            block = raw_df.iloc[data_start:, [product_col, qty_col, amt_col, stock_col]].copy()
            block.columns = ["product_code", "total_sales_qty", "total_sales_amt", "total_stock"]
            # Skip cells this branch had no figures for at all (most cells, in a wide report).
            blank_mask = block[["total_sales_qty", "total_sales_amt", "total_stock"]].isna().all(axis=1)
            block = block[~blank_mask]
            block["branch"] = branch_name
            frames.append(block)

        long_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
            columns=["product_code", "total_sales_qty", "total_sales_amt", "total_stock", "branch"]
        )
        long_df["product_code"] = long_df["product_code"].apply(normalize_text)
        long_df = long_df[long_df["product_code"] != ""]
        long_df.reset_index(drop=True, inplace=True)
        long_df.index = long_df.index + 1
        return long_df

    def process_chunk(self, chunk_df: pd.DataFrame):
        required = {"product_code", "branch", "total_sales_qty", "total_sales_amt", "total_stock"}
        missing_cols = required - set(chunk_df.columns)
        if missing_cols:
            return 0, 0, 0, [f"Internal error: missing columns {', '.join(sorted(missing_cols))}."]

        df = chunk_df.copy()
        df["product_code"] = df["product_code"].apply(normalize_text)
        df["branch"] = df["branch"].apply(normalize_text)
        for col in ["total_sales_qty", "total_sales_amt", "total_stock"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        bad_mask = (
            (df["product_code"] == "") | (df["branch"] == "")
            | df["total_sales_qty"].isna() | df["total_sales_amt"].isna() | df["total_stock"].isna()
        )
        bad_count = int(bad_mask.sum())
        df = df[~bad_mask]

        errors = []
        if bad_count:
            errors.append(f"{bad_count} row(s) skipped - missing product code/branch or non-numeric sales figures.")

        if df.empty:
            return 0, 0, 0, errors

        # De-duplicate within this chunk by (product_code, branch), keeping the last occurrence.
        df = df.drop_duplicates(subset=["product_code", "branch"], keep="last")

        # --- Resolve references; Product and Branch must already exist ----
        codes = set(df["product_code"].unique())
        product_map = {p.product_code: p for p in Product.objects.filter(product_code__in=codes)}
        missing_products = sorted(codes - set(product_map.keys()))
        if missing_products:
            errors.append(f"Unknown product code(s), row(s) skipped: {', '.join(missing_products)}.")
            df = df[df["product_code"].isin(product_map.keys())]

        if df.empty:
            return 0, 0, 0, errors

        branch_names = set(df["branch"].unique())
        branch_map = {b.name: b for b in Branch.objects.filter(name__in=branch_names)}
        missing_branches = sorted(branch_names - set(branch_map.keys()))
        if missing_branches:
            errors.append(
                f"Unknown branch name(s), row(s) skipped: {', '.join(missing_branches)}. "
                "Upload them via the Branches module first."
            )
            df = df[df["branch"].isin(branch_map.keys())]

        if df.empty:
            return 0, 0, 0, errors

        rows = list(df.itertuples(index=False))
        codes_in_chunk = [r.product_code for r in rows]
        branches_in_chunk = [r.branch for r in rows]
        chunk_keys = set(zip(codes_in_chunk, branches_in_chunk))

        existing_before_candidates = set(
            SalesData.objects.filter(
                start_date=self._start_date, end_date=self._end_date,
                product__product_code__in=codes_in_chunk, branch__name__in=branches_in_chunk,
            ).values_list("product__product_code", "branch__name")
        )
        # The query above is a superset (any matching code with any matching branch,
        # not necessarily paired) - intersect with this chunk's actual pairs to get
        # an accurate created-vs-updated count.
        existing_before = existing_before_candidates & chunk_keys

        objs = [
            SalesData(
                product=product_map[r.product_code],
                branch=branch_map[r.branch],
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
            update_fields=["total_sales_qty", "total_sales_amt", "total_stock"],
            unique_fields=["product", "branch", "start_date", "end_date"],
            batch_size=self.chunk_size,
        )

        updated = len(existing_before)
        created = len(objs) - updated
        return created, updated, 0, errors

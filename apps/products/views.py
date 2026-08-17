import logging

from django.contrib.auth import get_user_model
from django.db.models import CharField, Q, Value
from django.db.models.functions import Concat, Trim
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView
from django_tables2 import SingleTableMixin

from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin
from apps.core.utils import normalize_text

from .forms import ProductForm
from .models import Product
from .tables import ProductTable

logger = logging.getLogger("apps.products")
User = get_user_model()


class ProductListView(SingleTableMixin, CrudPermissionMixin, ListView):
    model = Product
    permission_required = "products.view_product"
    template_name = "products/list.html"
    table_class = ProductTable

    def get_queryset(self):
        qs = Product.objects.select_related("admin", "buyer")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(product_code__icontains=q) | Q(description__icontains=q) | Q(department__icontains=q)
            )
        return qs

    def get_table_kwargs(self):
        return {"request": self.request}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class ProductCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = Product
    form_class = ProductForm
    permission_required = "products.add_product"
    template_name = "products/form.html"
    success_url = reverse_lazy("products:list")
    success_message = "Product created successfully."


class ProductUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Product
    form_class = ProductForm
    permission_required = "products.change_product"
    template_name = "products/form.html"
    success_url = reverse_lazy("products:list")
    success_message = "Product updated successfully."


class ProductDeleteView(ObjectDeleteView):
    model = Product
    permission_required = "products.delete_product"
    success_url = reverse_lazy("products:list")
    success_message = "Product deleted successfully."


class ProductExcelUploadView(ExcelUploadView):
    """Columns expected: "Product Code", "Description", "Department",
    "Admin" (full name), "Buyer" (full name).

    Admin and Buyer must already exist as Users, matched by their full
    name (first name + last name), treated as a unique identifier.

    Upsert semantics: a row for a product_code that already exists
    updates that product's description/department/admin/buyer; a
    product_code that doesn't exist yet is created - via a single
    Postgres-native `INSERT ... ON CONFLICT (product_code) DO UPDATE`
    per chunk (bulk_create(update_conflicts=True)).
    """

    permission_required = "products.add_product"
    success_url = reverse_lazy("products:list")
    entity_label = "products"
    upload_title = "Bulk Upload Products"
    expected_columns = ["Product Code", "Description", "Department", "Admin (full name)", "Buyer (full name)"]

    REQUIRED_COLUMNS = {"product_code", "description", "department", "admin", "buyer"}

    def process_chunk(self, chunk_df):
        missing_cols = self.REQUIRED_COLUMNS - set(chunk_df.columns)
        if missing_cols:
            return 0, 0, 0, [f"The uploaded file must have columns: {', '.join(sorted(missing_cols))}."]

        rows = chunk_df[list(self.REQUIRED_COLUMNS)].copy()
        for col in self.REQUIRED_COLUMNS:
            rows[col] = rows[col].apply(normalize_text)

        blank_mask = (rows["product_code"] == "") | (rows["admin"] == "") | (rows["buyer"] == "")
        blank_count = int(blank_mask.sum())
        rows = rows[~blank_mask]

        errors = []
        if blank_count:
            errors.append(f"{blank_count} row(s) skipped - missing 'Product Code', 'Admin' or 'Buyer' value.")

        if rows.empty:
            return 0, 0, 0, errors

        # De-duplicate within this chunk, keeping the last occurrence of a product_code.
        rows = rows.drop_duplicates(subset="product_code", keep="last")

        # --- Resolve Admin/Buyer by full name (must already exist) --------
        full_names = set(rows["admin"].unique()) | set(rows["buyer"].unique())
        user_map = {
            u.full_name: u
            for u in User.objects.annotate(
                full_name=Trim(Concat("first_name", Value(" "), "last_name", output_field=CharField()))
            ).filter(full_name__in=full_names)
        }
        missing_names = sorted(full_names - set(user_map.keys()))
        if missing_names:
            errors.append(
                f"No user found with full name(s): {', '.join(missing_names)}. Create the user in the admin panel first."
            )
            rows = rows[rows["admin"].isin(user_map.keys()) & rows["buyer"].isin(user_map.keys())]

        if rows.empty:
            return 0, 0, 0, errors

        codes = rows["product_code"].tolist()
        existing_before = set(Product.objects.filter(product_code__in=codes).values_list("product_code", flat=True))

        objs = [
            Product(
                product_code=r.product_code, description=r.description, department=r.department,
                admin=user_map[r.admin], buyer=user_map[r.buyer], is_active=True,
            )
            for r in rows.itertuples(index=False)
        ]

        Product.objects.bulk_create(
            objs,
            update_conflicts=True,
            update_fields=["description", "department", "admin", "buyer"],
            unique_fields=["product_code"],
            batch_size=self.chunk_size,
        )

        updated = len(existing_before)
        created = len(objs) - updated
        return created, updated, 0, errors

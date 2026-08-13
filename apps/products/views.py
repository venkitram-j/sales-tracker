import logging

from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView

from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin
from apps.departments.models import Department

from .forms import ProductForm
from .models import Product

logger = logging.getLogger("apps.products")


class ProductListView(CrudPermissionMixin, ListView):
    model = Product
    permission_required = "products.view_product"
    template_name = "products/list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        qs = Product.objects.select_related("department")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(product_code__icontains=q) | Q(description__icontains=q))
        department_id = self.request.GET.get("department")
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs.order_by("product_code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["departments"] = Department.objects.filter(is_active=True).order_by("name")
        ctx["selected_department"] = self.request.GET.get("department", "")
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
    """Columns expected: "Product Code", "Description", "Department".

    The referenced Department must already exist (upload it via the
    Departments module first) - this view does not auto-create master
    data, only Products. Existing products (matched by product_code) are
    skipped rather than duplicated.
    """

    permission_required = "products.add_product"
    success_url = reverse_lazy("products:list")
    entity_label = "products"
    upload_title = "Bulk Upload Products"
    expected_columns = ["Product Code", "Description", "Department"]

    def process_chunk(self, chunk_df):
        required = {"product_code", "description", "department"}
        missing_cols = required - set(chunk_df.columns)
        if missing_cols:
            return 0, 0, 0, [f"The uploaded file must have columns: {', '.join(sorted(missing_cols))}."]

        rows = chunk_df[["product_code", "description", "department"]].copy()
        rows["product_code"] = rows["product_code"].astype(str).str.strip()
        rows["description"] = rows["description"].astype(str).str.strip()
        rows["department"] = rows["department"].astype(str).str.strip()

        blank_mask = (rows["product_code"] == "") | (rows["department"] == "")
        blank_count = int(blank_mask.sum())
        rows = rows[~blank_mask]

        errors = []
        if blank_count:
            errors.append(f"{blank_count} row(s) skipped - missing 'Product Code' or 'Department' value.")

        if rows.empty:
            return 0, 0, 0, errors

        # De-duplicate within this chunk, keeping the last occurrence of a product_code.
        rows = rows.drop_duplicates(subset="product_code", keep="last")

        dept_names = set(rows["department"].unique())
        dept_map = {d.name: d for d in Department.objects.filter(name__in=dept_names)}
        missing_depts = sorted(dept_names - set(dept_map.keys()))
        if missing_depts:
            errors.append(
                f"Unknown department(s) - row(s) skipped: {', '.join(missing_depts)}. "
                "Upload these via the Departments module first."
            )
            rows = rows[rows["department"].isin(dept_map.keys())]

        if rows.empty:
            return 0, 0, 0, errors

        codes = rows["product_code"].tolist()
        existing_before = Product.objects.filter(product_code__in=codes).count()

        Product.objects.bulk_create(
            [
                Product(
                    product_code=r.product_code, description=r.description,
                    department=dept_map[r.department], is_active=True,
                )
                for r in rows.itertuples(index=False)
            ],
            batch_size=self.chunk_size,
            ignore_conflicts=True,
        )

        existing_after = Product.objects.filter(product_code__in=codes).count()
        created = existing_after - existing_before
        skipped = len(codes) - created
        return created, 0, skipped, errors

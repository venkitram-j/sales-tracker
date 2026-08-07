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
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(category__icontains=q))
        department_id = self.request.GET.get("department")
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs.order_by("name")

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
    permission_required = "products.add_product"
    success_url = reverse_lazy("products:list")
    entity_label = "products"
    upload_title = "Bulk Upload Products"
    expected_columns = ["name", "sku", "department_code", "department_name", "category", "description", "unit_price"]

    def process_row(self, row_number, row):
        name = (row.get("name") or "").strip()
        sku = (row.get("sku") or "").strip()
        if not name or not sku:
            raise ValueError("'name' and 'sku' are required.")
        unit_price = row.get("unit_price") or 0
        try:
            unit_price = float(unit_price)
        except (TypeError, ValueError):
            raise ValueError("'unit_price' must be numeric.")

        department = self._resolve_department(row)

        Product.objects.update_or_create(
            sku=sku,
            defaults={
                "name": name,
                "department": department,
                "category": (row.get("category") or "").strip(),
                "description": (row.get("description") or "").strip(),
                "unit_price": unit_price,
                "is_active": True,
            },
        )

    @staticmethod
    def _resolve_department(row):
        dept_code = (row.get("department_code") or "").strip()
        dept_name = (row.get("department_name") or "").strip()
        if not dept_code and not dept_name:
            raise ValueError("'department_code' or 'department_name' is required.")
        if dept_code:
            department, _ = Department.objects.get_or_create(
                code=dept_code, defaults={"name": dept_name or dept_code}
            )
        else:
            department, _ = Department.objects.get_or_create(
                name=dept_name, defaults={"code": dept_name[:32]}
            )
        return department

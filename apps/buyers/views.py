import logging

from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView

from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin
from apps.products.models import Product

from .forms import BuyerForm
from .models import Buyer

logger = logging.getLogger("apps.buyers")


class BuyerListView(CrudPermissionMixin, ListView):
    model = Buyer
    permission_required = "buyers.view_buyer"
    template_name = "buyers/list.html"
    context_object_name = "buyers"
    paginate_by = 25

    def get_queryset(self):
        qs = Buyer.objects.prefetch_related("products")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(company__icontains=q) | Q(email__icontains=q))
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class BuyerCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = Buyer
    form_class = BuyerForm
    permission_required = "buyers.add_buyer"
    template_name = "buyers/form.html"
    success_url = reverse_lazy("buyers:list")
    success_message = "Buyer created successfully."


class BuyerUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Buyer
    form_class = BuyerForm
    permission_required = "buyers.change_buyer"
    template_name = "buyers/form.html"
    success_url = reverse_lazy("buyers:list")
    success_message = "Buyer updated successfully."


class BuyerDeleteView(ObjectDeleteView):
    model = Buyer
    permission_required = "buyers.delete_buyer"
    success_url = reverse_lazy("buyers:list")
    success_message = "Buyer deleted successfully."


class BuyerExcelUploadView(ExcelUploadView):
    """Columns expected: name, company, email, phone, address, product_skus (comma separated)."""

    permission_required = "buyers.add_buyer"
    success_url = reverse_lazy("buyers:list")
    entity_label = "buyers"
    upload_title = "Bulk Upload Buyers"
    expected_columns = ["name", "company", "email", "phone", "address", "product_skus (comma separated)"]

    def process_row(self, row_number, row):
        name = (row.get("name") or "").strip()
        if not name:
            raise ValueError("'name' is required.")
        email = (row.get("email") or "").strip()

        lookup = {"email": email} if email else {"name": name}
        buyer, _ = Buyer.objects.update_or_create(
            **lookup,
            defaults={
                "name": name,
                "company": (row.get("company") or "").strip(),
                "email": email,
                "phone": (row.get("phone") or "").strip(),
                "address": (row.get("address") or "").strip(),
                "is_active": True,
            },
        )

        sku_raw = (row.get("product_skus") or row.get("products") or "").strip()
        if sku_raw:
            skus = [s.strip() for s in sku_raw.split(",") if s.strip()]
            products = list(Product.objects.filter(sku__in=skus))
            found = {p.sku for p in products}
            missing = set(skus) - found
            if missing:
                raise ValueError(f"Unknown product SKU(s): {', '.join(missing)}")
            buyer.products.set(products)

import logging
import pandas as pd

from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView

from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin

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
        qs = Buyer.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q))
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
    """Single-column upload: the file's only expected column is "Buyer"
    (matching the model name). Existing buyers (matched by name) are
    skipped rather than duplicated - see DepartmentExcelUploadView for the
    identical Postgres-native skip-existing pattern.
    """

    permission_required = "buyers.add_buyer"
    success_url = reverse_lazy("buyers:list")
    entity_label = "buyers"
    upload_title = "Bulk Upload Buyers"
    expected_columns = ["Buyer"]

    def process_chunk(self, chunk_df: pd.DataFrame):
        if "buyer" not in chunk_df.columns:
            return 0, 0, 0, ["The uploaded file must have a 'Buyer' column."]

        chunk_df = chunk_df.dropna(subset=["buyer"], how="all")
        names = chunk_df["buyer"].astype(str).str.strip()
        blank_count = int((names == "").sum() + names.isna().sum())
        names = names[(names != "") & names.notna()].drop_duplicates(keep="last")

        errors = []
        if blank_count:
            errors.append(f"{blank_count} row(s) skipped - missing 'Buyer' value.")

        if names.empty:
            return 0, 0, 0, errors

        name_list = names.tolist()
        existing_before = Buyer.objects.filter(name__in=name_list).count()

        Buyer.objects.bulk_create(
            [Buyer(name=n, is_active=True) for n in name_list],
            batch_size=self.chunk_size,
            ignore_conflicts=True,
        )

        existing_after = Buyer.objects.filter(name__in=name_list).count()
        created = existing_after - existing_before
        skipped = len(name_list) - created
        return created, 0, skipped, errors

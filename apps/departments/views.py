import logging
import pandas as pd

from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView

from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin

from .forms import DepartmentForm
from .models import Department

logger = logging.getLogger("apps.departments")


class DepartmentListView(CrudPermissionMixin, ListView):
    model = Department
    permission_required = "departments.view_department"
    template_name = "departments/list.html"
    context_object_name = "departments"
    paginate_by = 25

    def get_queryset(self):
        qs = Department.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q))
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class DepartmentCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    permission_required = "departments.add_department"
    template_name = "departments/form.html"
    success_url = reverse_lazy("departments:list")
    success_message = "Department created successfully."


class DepartmentUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    permission_required = "departments.change_department"
    template_name = "departments/form.html"
    success_url = reverse_lazy("departments:list")
    success_message = "Department updated successfully."


class DepartmentDeleteView(ObjectDeleteView):
    model = Department
    permission_required = "departments.delete_department"
    success_url = reverse_lazy("departments:list")
    success_message = "Department deleted successfully."


class DepartmentExcelUploadView(ExcelUploadView):
    """Single-column upload: the file's only expected column is "Department"
    (matching the model name, per the app's upload convention).

    Existing departments (matched by name) are skipped rather than
    duplicated, using a single Postgres-native `INSERT ... ON CONFLICT DO
    NOTHING` per chunk (via bulk_create(ignore_conflicts=True)) - no
    per-row existence query.
    """

    permission_required = "departments.add_department"
    success_url = reverse_lazy("departments:list")
    entity_label = "departments"
    upload_title = "Bulk Upload Departments"
    expected_columns = ["Department"]

    def process_chunk(self, chunk_df: pd.DataFrame):
        if "department" not in chunk_df.columns:
            return 0, 0, 0, ["The uploaded file must have a 'Department' column."]

        chunk_df = chunk_df.dropna(subset=["department"], how="all")
        names = chunk_df["department"].astype(str).str.strip()
        blank_count = int((names == "").sum() + names.isna().sum())
        names = names[(names != "") & names.notna()].drop_duplicates(keep="last")

        errors = []
        if blank_count:
            errors.append(f"{blank_count} row(s) skipped - missing 'Department' value.")

        if names.empty:
            return 0, 0, 0, errors

        name_list = names.tolist()
        existing_before = Department.objects.filter(name__in=name_list).count()

        Department.objects.bulk_create(
            [Department(name=n, is_active=True) for n in name_list],
            batch_size=self.chunk_size,
            ignore_conflicts=True,
        )

        existing_after = Department.objects.filter(name__in=name_list).count()
        created = existing_after - existing_before
        skipped = len(name_list) - created
        return created, 0, skipped, errors

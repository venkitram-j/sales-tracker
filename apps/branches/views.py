import logging

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView

from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, FilteredTableListView, ObjectDeleteView, SuccessMessageMixin
from apps.core.utils import normalize_text

from .filters import BranchFilter
from .forms import BranchForm
from .models import Branch
from .tables import BranchTable

logger = logging.getLogger("apps.branches")


class BranchListView(FilteredTableListView):
    model = Branch
    permission_required = "branches.view_branch"
    template_name = "branches/list.html"
    table_class = BranchTable
    filterset_class = BranchFilter


class BranchCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = Branch
    form_class = BranchForm
    permission_required = "branches.add_branch"
    template_name = "branches/form.html"
    success_url = reverse_lazy("branches:list")
    success_message = "Branch created successfully."


class BranchUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Branch
    form_class = BranchForm
    permission_required = "branches.change_branch"
    template_name = "branches/form.html"
    success_url = reverse_lazy("branches:list")
    success_message = "Branch updated successfully."


class BranchDeleteView(ObjectDeleteView):
    model = Branch
    permission_required = "branches.delete_branch"
    success_url = reverse_lazy("branches:list")
    success_message = "Branch deleted successfully."


class BranchExcelUploadView(ExcelUploadView):
    """Single-column upload: the file's only expected column is "Branch"
    (matching the model name). Existing branches (matched by name) are
    skipped rather than duplicated, via a single Postgres-native
    `INSERT ... ON CONFLICT DO NOTHING` per chunk.
    """

    permission_required = "branches.add_branch"
    success_url = reverse_lazy("branches:list")
    entity_label = "branches"
    upload_title = "Bulk Upload Branches"
    expected_columns = ["Branch"]

    def process_chunk(self, chunk_df):
        if "branch" not in chunk_df.columns:
            return 0, 0, 0, ["The uploaded file must have a 'Branch' column."]

        names = chunk_df["branch"].apply(normalize_text)
        blank_count = int((names == "").sum())
        names = names[names != ""].drop_duplicates(keep="last")

        errors = []
        if blank_count:
            errors.append(f"{blank_count} row(s) skipped - missing 'Branch' value.")

        if names.empty:
            return 0, 0, 0, errors

        name_list = names.tolist()
        existing_before = Branch.objects.filter(name__in=name_list).count()

        Branch.objects.bulk_create(
            [Branch(name=n, is_active=True) for n in name_list],
            batch_size=self.chunk_size,
            ignore_conflicts=True,
        )

        existing_after = Branch.objects.filter(name__in=name_list).count()
        created = existing_after - existing_before
        skipped = len(name_list) - created
        return created, 0, skipped, errors

import logging

from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView

from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin

from .forms import BranchForm
from .models import Branch

logger = logging.getLogger("apps.branches")


class BranchListView(CrudPermissionMixin, ListView):
    model = Branch
    permission_required = "branches.view_branch"
    template_name = "branches/list.html"
    context_object_name = "branches"
    paginate_by = 25

    def get_queryset(self):
        qs = Branch.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q))
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


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
    skipped rather than duplicated - see DepartmentExcelUploadView for the
    identical Postgres-native skip-existing pattern.
    """

    permission_required = "branches.add_branch"
    success_url = reverse_lazy("branches:list")
    entity_label = "branches"
    upload_title = "Bulk Upload Branches"
    expected_columns = ["Branch"]

    def process_chunk(self, chunk_df):
        if "branch" not in chunk_df.columns:
            return 0, 0, 0, ["The uploaded file must have a 'Branch' column."]

        names = chunk_df["branch"].astype(str).str.strip()
        blank_count = int((names == "").sum() + names.isna().sum())
        names = names[(names != "") & names.notna()].drop_duplicates(keep="last")

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

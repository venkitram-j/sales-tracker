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
    permission_required = "branches.add_branch"
    success_url = reverse_lazy("branches:list")
    entity_label = "branches"
    upload_title = "Bulk Upload Branches"
    expected_columns = ["branch"]

    def process_row(self, row_number, row):
        branch_name = (row.get("branch") or "").strip()
        if not branch_name:
            raise ValueError("'branch' is required.")

        Branch.objects.update_or_create(name=branch_name)

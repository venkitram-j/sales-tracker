import logging

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
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
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
    permission_required = "departments.add_department"
    success_url = reverse_lazy("departments:list")
    entity_label = "departments"
    upload_title = "Bulk Upload Departments"
    expected_columns = ["name", "code", "description"]

    def process_row(self, row_number, row):
        name = (row.get("name") or "").strip()
        code = (row.get("code") or "").strip()
        if not name or not code:
            raise ValueError("'name' and 'code' are required.")

        Department.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": (row.get("description") or "").strip(),
                "is_active": True,
            },
        )

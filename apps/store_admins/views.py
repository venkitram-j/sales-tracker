import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView

from apps.branches.models import Branch
from apps.core.mixins import CrudPermissionMixin, ExcelUploadView, ObjectDeleteView, SuccessMessageMixin

from .forms import StoreAdminForm
from .models import StoreAdmin

logger = logging.getLogger("apps.store_admins")
User = get_user_model()


class StoreAdminListView(CrudPermissionMixin, ListView):
    model = StoreAdmin
    permission_required = "store_admins.view_storeadmin"
    template_name = "store_admins/list.html"
    context_object_name = "store_admins"
    paginate_by = 25

    def get_queryset(self):
        qs = StoreAdmin.objects.select_related("user").prefetch_related("branches")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class StoreAdminCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = StoreAdmin
    form_class = StoreAdminForm
    permission_required = "store_admins.add_storeadmin"
    template_name = "store_admins/form.html"
    success_url = reverse_lazy("store_admins:list")
    success_message = "Store admin created successfully."


class StoreAdminUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = StoreAdmin
    form_class = StoreAdminForm
    permission_required = "store_admins.change_storeadmin"
    template_name = "store_admins/form.html"
    success_url = reverse_lazy("store_admins:list")
    success_message = "Store admin updated successfully."


class StoreAdminDeleteView(ObjectDeleteView):
    model = StoreAdmin
    permission_required = "store_admins.delete_storeadmin"
    success_url = reverse_lazy("store_admins:list")
    success_message = "Store admin removed successfully."


class StoreAdminExcelUploadView(ExcelUploadView):
    """Columns expected: email, branch_codes (comma separated), phone.

    The referenced user account must already exist (created via the admin
    panel); this view only attaches branch-management responsibility.
    """

    permission_required = "store_admins.add_storeadmin"
    success_url = reverse_lazy("store_admins:list")
    entity_label = "store admins"
    upload_title = "Bulk Upload Store Admins"
    expected_columns = ["email", "phone", "branch_codes (comma separated)"]

    def process_row(self, row_number, row):
        email = (row.get("email") or "").strip().lower()
        if not email:
            raise ValueError("'email' is required.")
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ValueError(f"No user found with email '{email}'. Create the user in the admin panel first.")

        store_admin, _ = StoreAdmin.objects.update_or_create(
            user=user,
            defaults={"phone": (row.get("phone") or "").strip(), "is_active": True},
        )

        branch_codes_raw = (row.get("branch_codes") or row.get("branches") or "").strip()
        if branch_codes_raw:
            codes = [c.strip() for c in branch_codes_raw.split(",") if c.strip()]
            branches = list(Branch.objects.filter(code__in=codes))
            found_codes = {b.code for b in branches}
            missing = set(codes) - found_codes
            if missing:
                raise ValueError(f"Unknown branch code(s): {', '.join(missing)}")
            store_admin.branches.set(branches)

import logging
import pandas as pd

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
    """Two columns expected: "Admin" (the user's email - the account must
    already exist, created via the admin panel) and "Branch" (a branch
    name that already exists in the Branches module). One row per
    admin+branch pairing - if the same admin manages several branches,
    give them one row per branch; they're aggregated automatically.

    Existence is checked by the linked user before inserting - a user who
    already has a Store Admin record is skipped rather than duplicated
    (their branch assignments from this file are still applied).
    """

    permission_required = "store_admins.add_storeadmin"
    success_url = reverse_lazy("store_admins:list")
    entity_label = "store admins"
    upload_title = "Bulk Upload Store Admins"
    expected_columns = ["Admin (email)", "Branch"]

    def process_chunk(self, chunk_df: pd.DataFrame):
        if "admin" not in chunk_df.columns or "branch" not in chunk_df.columns:
            return 0, 0, 0, ["The uploaded file must have 'Admin' and 'Branch' columns."]

        pairs = chunk_df[["admin", "branch"]].copy()
        pairs["admin"] = pairs["admin"].astype(str).str.strip().str.lower()
        pairs["branch"] = pairs["branch"].astype(str).str.strip()

        blank_mask = (pairs["admin"] == "") | (pairs["branch"] == "")
        blank_count = int(blank_mask.sum())
        pairs = pairs[~blank_mask]

        errors = []
        if blank_count:
            errors.append(f"{blank_count} row(s) skipped - missing 'Admin' or 'Branch' value.")

        if pairs.empty:
            return 0, 0, 0, errors

        # One admin -> many branches within this chunk, aggregated via groupby (vectorized).
        grouped = pairs.groupby("admin")["branch"].apply(lambda s: sorted(set(s))).to_dict()

        emails = list(grouped.keys())
        user_map = {u.email.lower(): u for u in User.objects.filter(email__in=emails)}
        missing_emails = sorted(set(emails) - set(user_map.keys()))
        for email in missing_emails:
            errors.append(f"No user found with email '{email}'. Create the user in the admin panel first.")

        resolvable = {email: branches for email, branches in grouped.items() if email in user_map}
        if not resolvable:
            return 0, 0, 0, errors

        user_ids = [user_map[email].id for email in resolvable]
        existing_before = set(StoreAdmin.objects.filter(user_id__in=user_ids).values_list("user_id", flat=True))

        to_create = [
            StoreAdmin(user=user_map[email], is_active=True)
            for email in resolvable
            if user_map[email].id not in existing_before
        ]
        StoreAdmin.objects.bulk_create(to_create, batch_size=self.chunk_size, ignore_conflicts=True)

        admin_by_user_id = {a.user_id: a for a in StoreAdmin.objects.filter(user_id__in=user_ids)}
        created = len(admin_by_user_id) - len(existing_before)
        skipped = len(resolvable) - created

        # Resolve branch names once for the whole chunk, then bulk-attach via the through-table.
        all_branch_names = {b for branches in resolvable.values() for b in branches}
        branch_map = {b.name: b for b in Branch.objects.filter(name__in=all_branch_names)}
        missing_branch_names = sorted(all_branch_names - set(branch_map.keys()))
        if missing_branch_names:
            errors.append(f"Unknown branch name(s), so not attached to any admin: {', '.join(missing_branch_names)}.")

        through_rows = []
        for email, branches in resolvable.items():
            admin = admin_by_user_id.get(user_map[email].id)
            if not admin:
                continue
            for branch_name in branches:
                branch = branch_map.get(branch_name)
                if branch:
                    through_rows.append(StoreAdmin.branches.through(storeadmin_id=admin.id, branch_id=branch.id))
        if through_rows:
            StoreAdmin.branches.through.objects.bulk_create(
                through_rows, batch_size=self.chunk_size, ignore_conflicts=True
            )

        return created, 0, skipped, errors

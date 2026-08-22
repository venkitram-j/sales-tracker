import django_tables2 as tables
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html

from apps.core.tables import BaseTable

User = get_user_model()


class UserTable(BaseTable):
    is_staff = tables.Column(verbose_name="Role")
    is_active = tables.Column(verbose_name="Status")
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = User
        fields = ("full_name", "email", "is_staff", "is_active", "actions")
        sequence = ("full_name", "email", "is_staff", "is_active", "actions")
        order_by = ("full_name",)
        template_name = "django_tables2/bootstrap5.html"

    def render_full_name(self, value):
        return value or "—"

    def render_is_staff(self, value):
        if value:
            return format_html('<span class="badge text-bg-primary">Staff</span>')
        return format_html('<span class="badge text-bg-light border">Standard</span>')

    def render_is_active(self, value):
        if value:
            return format_html('<span class="badge text-bg-success">Active</span>')
        return format_html('<span class="badge text-bg-secondary">Inactive</span>')

    def render_actions(self, record):
        edit_html = self.link_button(
            reverse("accounts:user_edit", args=[record.pk]) if self.user_has_perm("accounts.change_user") else None,
            "bi-pencil", "btn-outline-primary", title="Edit",
        )
        reset_html = self.link_button(
            reverse("accounts:user_password_reset", args=[record.pk]) if self.user_has_perm("accounts.change_user") else None,
            "bi-key", "btn-outline-secondary", title="Reset Password",
        )
        return format_html('<div class="text-end text-nowrap">{}{}</div>', edit_html, reset_html)

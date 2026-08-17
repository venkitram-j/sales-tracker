import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html

from apps.core.tables import BaseTable

from .models import Branch


class BranchTable(BaseTable):
    is_active = tables.Column(verbose_name="Status")
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Branch
        fields = ("name", "is_active", "actions")
        sequence = ("name", "is_active", "actions")
        order_by = ("name",)
        template_name = "django_tables2/bootstrap5.html"

    def render_is_active(self, value):
        if value:
            return format_html('<span class="badge text-bg-success">Active</span>')
        return format_html('<span class="badge text-bg-secondary">Inactive</span>')

    def render_actions(self, record):
        return self.action_buttons(
            edit_url=reverse("branches:edit", args=[record.pk]) if self.user_has_perm("branches.change_branch") else None,
            delete_url=reverse("branches:delete", args=[record.pk]) if self.user_has_perm("branches.delete_branch") else None,
            item_name=record.name,
        )

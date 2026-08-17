import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html

from apps.core.tables import BaseTable

from .models import Product


class ProductTable(BaseTable):
    is_active = tables.Column(verbose_name="Status")
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = Product
        fields = ("product_code", "description", "department", "admin", "buyer", "is_active", "actions")
        sequence = ("product_code", "description", "department", "admin", "buyer", "is_active", "actions")
        order_by = ("product_code",)
        template_name = "django_tables2/bootstrap5.html"

    def render_admin(self, value):
        return value.get_full_name() or value.email

    def render_buyer(self, value):
        return value.get_full_name() or value.email

    def render_is_active(self, value):
        if value:
            return format_html('<span class="badge text-bg-success">Active</span>')
        return format_html('<span class="badge text-bg-secondary">Inactive</span>')

    def render_actions(self, record):
        return self.action_buttons(
            edit_url=reverse("products:edit", args=[record.pk]) if self.user_has_perm("products.change_product") else None,
            delete_url=reverse("products:delete", args=[record.pk]) if self.user_has_perm("products.delete_product") else None,
            item_name=record.product_code,
        )

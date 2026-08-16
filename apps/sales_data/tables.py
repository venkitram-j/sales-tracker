import django_tables2 as tables
from django.urls import reverse

from apps.core.tables import BaseTable

from .models import SalesData


class SalesDataTable(BaseTable):
    product = tables.Column(verbose_name="Product Code", accessor="product__product_code", order_by="product__product_code")
    description = tables.Column(verbose_name="Description", accessor="product__description", orderable=False)
    branch = tables.Column(verbose_name="Branch", accessor="branch__name", order_by="branch__name")
    period = tables.Column(verbose_name="Period", accessor="start_date", orderable=True, order_by=("start_date", "end_date"))
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = SalesData
        fields = ("product", "description", "branch", "total_sales_qty", "total_sales_amt", "total_stock", "period", "actions")
        sequence = ("product", "description", "branch", "total_sales_qty", "total_sales_amt", "total_stock", "period", "actions")
        order_by = ("-start_date",)
        template_name = "django_tables2/bootstrap5.html"

    def render_period(self, record):
        return f"{record.start_date} – {record.end_date}"

    def render_actions(self, record):
        return self.action_buttons(
            edit_url=reverse("sales_data:edit", args=[record.pk]) if self.user_has_perm("sales_data.change_salesdata") else None,
            delete_url=reverse("sales_data:delete", args=[record.pk]) if self.user_has_perm("sales_data.delete_salesdata") else None,
            item_name=f"{record.product.product_code} @ {record.branch.name} ({record.start_date} - {record.end_date})",
        )


class SalesDataBranchWiseTable(tables.Table):
    """Backed by a plain list of flat dicts (see SalesDataBranchWiseView.get_table_data),
    not a queryset - simple, non-dunder column names sidestep any ambiguity in how
    django-tables2's Accessor would otherwise split a "__" key for nested lookup.
    """

    branch = tables.Column(verbose_name="Branch")
    product_code = tables.Column(verbose_name="Product Code")
    description = tables.Column(verbose_name="Description")
    transaction_count = tables.Column(verbose_name="Transactions")
    total_quantity = tables.Column(verbose_name="Total Qty")
    total_value = tables.Column(verbose_name="Total Amt")
    total_stock = tables.Column(verbose_name="Total Stock")

    class Meta:
        order_by = ("branch", "product_code")
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-hover mb-0 align-middle"}

    def render_total_value(self, value):
        return f"{value:.2f}" if value is not None else "—"

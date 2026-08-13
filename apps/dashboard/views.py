import logging

from django.db.models import Sum, Count
from django.views.generic import TemplateView

from apps.branches.models import Branch
from apps.core.mixins import AppLoginRequiredMixin
from apps.products.models import Product
from apps.salesdata.models import SalesData

logger = logging.getLogger("apps.dashboard")


class DashboardView(AppLoginRequiredMixin, TemplateView):
    """Landing page: interactive summary table of sales data plus KPIs."""

    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = SalesData.objects.select_related("product_code", "branch", "department", "admin__user", "buyer")

        totals = qs.aggregate(total_qty=Sum("total_sales_qty"), total_value=Sum("total_sales_amt"))
        ctx["total_quantity"] = totals["total_qty"] or 0
        ctx["total_value"] = totals["total_value"] or 0
        ctx["product_count"] = Product.objects.filter(is_active=True).count()
        ctx["branch_count"] = Branch.objects.filter(is_active=True).count()

        ctx["branch_summary"] = (
            qs.values("branch__name")
            .annotate(total_quantity=Sum("total_sales_qty"), total_value=Sum("total_sales_amt"), tx_count=Count("id"))
            .order_by("-total_value")[:10]
        )
        ctx["recent_sales"] = qs.order_by("-start_date", "-created_at")[:15]
        return ctx

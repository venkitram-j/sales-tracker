from django.contrib import admin

from .models import SalesData


@admin.register(SalesData)
class SalesDataAdmin(admin.ModelAdmin):
    list_display = ("product", "branch", "total_sales_qty", "total_sales_amt", "total_stock", "start_date", "end_date")
    list_filter = ("branch", "start_date")
    search_fields = ("product__product_code", "product__description", "branch__name")
    date_hierarchy = "start_date"
    autocomplete_fields = ["product", "branch"]

from django.contrib import admin

from .models import SalesData


@admin.action(description="Mark reviewed (example bulk action)")
def mark_reviewed(modeladmin, request, queryset):
    modeladmin.message_user(request, f"{queryset.count()} record(s) marked reviewed.")


@admin.register(SalesData)
class SalesDataAdmin(admin.ModelAdmin):
    list_display = (
        "product", "branch", "department", "buyer", "admin",
        "sales_quantity", "sales_value", "total_stock", "start_date", "end_date",
    )
    list_filter = ("branch", "department", "product", "start_date")
    search_fields = ("product__name", "branch__name", "department__name", "admin__user__email", "buyer__name")
    date_hierarchy = "start_date"
    autocomplete_fields = ["product", "branch", "department", "admin", "buyer"]
    actions = [mark_reviewed]

from django.contrib import admin

from .models import Product


@admin.action(description="Mark selected products as active")
def mark_active(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} product(s) marked active.")


@admin.action(description="Mark selected products as inactive")
def mark_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} product(s) marked inactive.")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "unit_price", "is_active", "updated_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "sku", "category")
    ordering = ("name",)
    actions = [mark_active, mark_inactive]

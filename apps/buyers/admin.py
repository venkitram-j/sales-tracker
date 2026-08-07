from django.contrib import admin

from .models import Buyer


@admin.action(description="Mark selected buyers as active")
def mark_active(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} buyer(s) marked active.")


@admin.action(description="Mark selected buyers as inactive")
def mark_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} buyer(s) marked inactive.")


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "email", "phone", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "company", "email")
    filter_horizontal = ("products",)
    actions = [mark_active, mark_inactive]

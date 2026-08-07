from django.contrib import admin

from .models import Branch


@admin.action(description="Mark selected branches as active")
def mark_active(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} branch(es) marked active.")


@admin.action(description="Mark selected branches as inactive")
def mark_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} branch(es) marked inactive.")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "state", "is_active", "updated_at")
    list_filter = ("is_active", "state")
    search_fields = ("name", "code", "city", "state")
    ordering = ("name",)
    actions = [mark_active, mark_inactive]

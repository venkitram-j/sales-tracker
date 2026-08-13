from django.contrib import admin

from .models import StoreAdmin


@admin.action(description="Mark selected store admins as active")
def mark_active(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} store admin(s) marked active.")


@admin.action(description="Mark selected store admins as inactive")
def mark_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} store admin(s) marked inactive.")


@admin.register(StoreAdmin)
class StoreAdminAdmin(admin.ModelAdmin):
    list_display = ("full_name_display", "email_display", "branch_list_display", "is_active")
    list_filter = ("is_active", "branches")
    search_fields = ("user__first_name", "user__last_name", "user__email")
    filter_horizontal = ("branches",)
    autocomplete_fields = ["user"]
    actions = [mark_active, mark_inactive]

    @admin.display(description="Name")
    def full_name_display(self, obj):
        return obj.full_name

    @admin.display(description="Email")
    def email_display(self, obj):
        return obj.user.email

    @admin.display(description="Branches")
    def branch_list_display(self, obj):
        return obj.branch_list

"""
User Admin
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

User = get_user_model()


class EmailUserCreationForm(UserCreationForm):
    """User-creation form keyed on email; username/full_name are derived automatically."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")


class EmailUserChangeForm(UserChangeForm):
    """User-edit form keyed on email; username field is never shown."""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "user_permissions"
        ) # type: ignore


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Username is fully hidden from the admin UI; email is the identifier.
    """

    add_form = EmailUserCreationForm
    form = EmailUserChangeForm
    ordering = ("email",)
    list_display = ("email", "full_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("last_login", "date_joined", "full_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "full_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )

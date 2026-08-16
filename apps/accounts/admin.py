from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User


class EmailUserCreationForm(UserCreationForm):
    """User-creation form keyed on email; username is derived automatically."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


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
            "groups",
            "user_permissions",
        )


class UserAdmin(DjangoUserAdmin):
    """Username is fully hidden from the admin UI; email is the identifier.

    Password changes/resets continue to use Django's built-in
    "this form does not store the raw password" flow available from the
    user change page action link, satisfying the requirement that
    password resets only happen via the admin panel.
    """

    add_form = EmailUserCreationForm
    form = EmailUserChangeForm
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
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


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

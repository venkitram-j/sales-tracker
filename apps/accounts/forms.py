from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AdminPasswordChangeForm as DjangoAdminPasswordChangeForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    """Login form that collects an email + password instead of username."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "autofocus": True, "placeholder": "you@example.com"}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )

    error_messages = {
        "invalid_login": "Please enter a correct email and password. Both fields are case-sensitive for the password.",
        "inactive": "This account is inactive. Please contact your administrator.",
    }

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if email and password:
            self.user_cache = self.get_user_or_none(email, password)
            if self.user_cache is None:
                raise forms.ValidationError(self.error_messages["invalid_login"], code="invalid_login")
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    def get_user_or_none(self, email, password):
        from django.contrib.auth import authenticate

        return authenticate(self.request, username=email, password=password)


class UserManageFormBase(forms.ModelForm):
    """Shared base for the create/update user forms: Bootstrap styling plus
    a Groups checkbox list sourced live from whatever Groups exist (the
    three created by `python manage.py seed_groups` - Viewer, Branch
    Manager, Data Administrator - show up here automatically once seeded,
    same as any other Group).
    """

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Determines what this user can see and do - see the Permissions section of the README.",
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "is_active", "is_staff", "groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                widget.attrs["class"] = "form-check-input"
            else:
                widget.attrs["class"] = "form-control"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class UserCreateForm(UserManageFormBase):
    password1 = forms.CharField(
        label="Password", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="Confirm Password", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    field_order = ["email", "first_name", "last_name", "password1", "password2", "is_active", "is_staff", "groups"]

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        if password2:
            validate_password(password2)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserUpdateForm(UserManageFormBase):
    """No password fields - use the separate Reset Password page for that."""

    pass


class AdminPasswordChangeForm(DjangoAdminPasswordChangeForm):
    """Django's built-in admin-style "set a new password directly" form
    (no old-password confirmation needed), just restyled for Bootstrap.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

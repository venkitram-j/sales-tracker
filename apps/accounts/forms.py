"""
User forms
"""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    """
    Login form that collects an email + password instead of username.
    """

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
        return authenticate(self.request, username=email, password=password)

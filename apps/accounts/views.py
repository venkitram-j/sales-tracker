"""
User views
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView

from .forms import EmailAuthenticationForm

logger = logging.getLogger("apps.accounts")
User = get_user_model()


class EmailLoginView(LoginView):
    """
    Login page which authenticates via email + password.
    """

    template_name = "registration/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        logger.info("Successful login for %s", form.get_user().email)
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning("Failed login attempt for %s", self.request.POST.get("username"))
        return super().form_invalid(form)


class AppLogoutView(LogoutView):
    next_page = "accounts:login"

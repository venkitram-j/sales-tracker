import logging

from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

logger = logging.getLogger("apps.core.mixins")


class AppLoginRequiredMixin(LoginRequiredMixin):
    """Base mixin: every internal view requires an authenticated user."""

    login_url = reverse_lazy("accounts:login")

from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class DashboardView(LoginRequiredMixin, TemplateView):
    """Landing page"""

    template_name = "dashboard/dashboard.html"
    login_url = reverse_lazy("accounts:login")

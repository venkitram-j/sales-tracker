"""
Dashboard views
"""

import logging

from django.views.generic import TemplateView

from apps.core.mixins import AppLoginRequiredMixin

logger = logging.getLogger("apps.dashboard")


class DashboardView(AppLoginRequiredMixin, TemplateView):
    """Landing page."""

    template_name = "dashboard/dashboard.html"

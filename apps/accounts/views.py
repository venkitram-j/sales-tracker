import logging

from django.contrib.auth.views import LoginView, LogoutView

from .forms import EmailAuthenticationForm

logger = logging.getLogger("apps.accounts")


class EmailLoginView(LoginView):
    """Renders the login page and authenticates via email + password.

    User creation and password resets are intentionally NOT exposed here;
    they are handled exclusively through the Django admin panel per the
    application's access-control requirements.
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

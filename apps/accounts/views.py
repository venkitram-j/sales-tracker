import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, FormView, UpdateView

from apps.core.mixins import CrudPermissionMixin, FilteredTableListView, SuccessMessageMixin

from .filters import UserFilter
from .forms import AdminPasswordChangeForm, EmailAuthenticationForm, UserCreateForm, UserUpdateForm
from .tables import UserTable

logger = logging.getLogger("apps.accounts")
User = get_user_model()


class EmailLoginView(LoginView):
    """Renders the login page and authenticates via email + password.

    Self-service password resets are intentionally not exposed here;
    resetting a user's password is a staff-only action - see
    UserPasswordResetView below, reachable from the "Manage Users" sidebar
    menu for staff users (see apps.accounts.signals for how permissions
    are derived from is_staff).
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


class UserListView(FilteredTableListView):
    """Also doubles as the "Reset Password" landing page (the sidebar links
    here) - Edit and Reset Password are both per-row actions in the table.
    """

    model = User
    permission_required = "accounts.view_user"
    template_name = "accounts/user_list.html"
    table_class = UserTable
    filterset_class = UserFilter

    def get_base_queryset(self):
        return User.objects.all()


class UserCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UserCreateForm
    permission_required = "accounts.add_user"
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "User created successfully."


class UserUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    permission_required = "accounts.change_user"
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "User updated successfully."


class UserPasswordResetView(CrudPermissionMixin, SingleObjectMixin, FormView):
    """Admin-style password reset: set a new password directly, no email
    flow and no old-password confirmation. Django's own AdminPasswordChangeForm
    (see apps.accounts.forms) does the actual validation/hashing.
    """

    model = User
    form_class = AdminPasswordChangeForm
    permission_required = "accounts.change_user"
    template_name = "accounts/user_password_reset.html"
    success_url = reverse_lazy("accounts:user_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["target_user"] = self.object
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            f"Password reset for {self.object.full_name or self.object.email}.",
        )
        return super().form_valid(form)

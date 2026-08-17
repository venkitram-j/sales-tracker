import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, FormView, UpdateView
from django_tables2 import SingleTableMixin

from apps.core.mixins import CrudPermissionMixin, SuccessMessageMixin

from .forms import AdminPasswordChangeForm, EmailAuthenticationForm, UserCreateForm, UserUpdateForm
from .tables import UserTable

logger = logging.getLogger("apps.accounts")
User = get_user_model()


class EmailLoginView(LoginView):
    """Renders the login page and authenticates via email + password.

    Self-service password resets are intentionally not exposed here;
    resetting a user's password is an admin action - see
    UserPasswordResetView below, reachable from the "Manage Users" sidebar
    menu for users with the auth.change_user permission.
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


class UserListView(SingleTableMixin, CrudPermissionMixin, ListView):
    """Also doubles as the "Reset Password" landing page (the sidebar links
    here) - Edit and Reset Password are both per-row actions in the table.
    """

    model = User
    permission_required = "auth.view_user"
    template_name = "accounts/user_list.html"
    table_class = UserTable

    def get_queryset(self):
        qs = User.objects.prefetch_related("groups").order_by("first_name", "last_name")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs

    def get_table_kwargs(self):
        return {"request": self.request}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class UserCreateView(CrudPermissionMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UserCreateForm
    permission_required = "auth.add_user"
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = "User created successfully."


class UserUpdateView(CrudPermissionMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    permission_required = "auth.change_user"
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
    permission_required = "auth.change_user"
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
            f"Password reset for {self.object.get_full_name() or self.object.email}.",
        )
        return super().form_valid(form)

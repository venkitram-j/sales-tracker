import logging

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView

from apps.core.forms import ExcelUploadForm
from apps.core.utils import ExcelParseError, iter_excel_rows

logger = logging.getLogger("apps.core.mixins")


class AppLoginRequiredMixin(LoginRequiredMixin):
    """Base mixin: every internal view requires an authenticated user."""

    login_url = reverse_lazy("accounts:login")


class SuccessMessageMixin:
    """Adds a Django messages framework success message on valid form submission."""

    success_message = ""

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response


class CrudPermissionMixin(AppLoginRequiredMixin, PermissionRequiredMixin):
    """Combines login + Django's built-in permission framework.

    `permission_required` should be set on each concrete view, e.g.
    "products.add_product". Superusers and users holding the permission
    (directly or via a Group) pass automatically - this is native
    django.contrib.auth behaviour, nothing custom is implemented.
    """

    raise_exception = False  # redirected to login, or show 403 if authenticated but lacking perms

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission to perform this action.")
            from django.shortcuts import redirect

            return redirect(self.get_permission_denied_redirect())
        return super().handle_no_permission()

    def get_permission_denied_redirect(self):
        return reverse_lazy("dashboard:home")


class ExcelUploadView(CrudPermissionMixin, FormView):
    """Generic base view for bulk-creating/updating records from an .xlsx file.

    Subclasses must implement `process_row(row_number, row)` returning
    nothing on success and raising ValueError(message) on a recoverable
    per-row problem. Each row is committed independently so one bad row
    does not abort the whole file.
    """

    form_class = ExcelUploadForm
    template_name = "partials/excel_upload_form.html"
    entity_label = "records"
    upload_title = "Bulk Upload"
    expected_columns = []
    upload_help_text = ""
    list_url_name = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["upload_title"] = self.upload_title
        ctx["expected_columns"] = self.expected_columns
        ctx["upload_help_text"] = self.upload_help_text
        ctx["cancel_url"] = self.success_url
        return ctx

    def process_row(self, row_number, row):
        raise NotImplementedError

    def before_rows(self, form, uploaded_file, header_row):
        """Optional hook for subclasses that need to inspect the file (e.g.
        metadata sitting above the header row) before per-row processing
        starts. Raise ValueError with a user-facing message to abort the
        whole upload before any rows are processed. Must leave the file
        pointer at position 0 when done, since `iter_excel_rows` reads
        `uploaded_file` again immediately afterwards.
        """
        return None

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["excel_file"]
        header_row = form.cleaned_data["header_row"]
        data_start_row = form.cleaned_data.get("data_start_row")
        start_col = form.cleaned_data["start_column_index"]
        success_count = 0
        errors = []

        try:
            self.before_rows(form, uploaded_file, header_row)
        except ValueError as exc:
            messages.error(self.request, str(exc))
            return self.render_to_response(self.get_context_data(form=form))

        try:
            rows = list(
                iter_excel_rows(
                    uploaded_file,
                    header_row=header_row,
                    data_start_row=data_start_row,
                    start_col=start_col,
                )
            )
        except ExcelParseError as exc:
            messages.error(self.request, str(exc))
            return self.render_to_response(self.get_context_data(form=form))

        for row_number, row in rows:
            try:
                with transaction.atomic():
                    self.process_row(row_number, row)
                success_count += 1
            except ValueError as exc:
                errors.append(f"Row {row_number}: {exc}")
            except Exception:  # noqa: BLE001
                logger.exception("Unexpected error processing row %s", row_number)
                errors.append(f"Row {row_number}: unexpected error, see server logs.")

        if success_count:
            messages.success(self.request, f"Successfully imported {success_count} {self.entity_label}.")
        if errors:
            preview = "; ".join(errors[:10])
            more = f" (+{len(errors) - 10} more)" if len(errors) > 10 else ""
            messages.warning(self.request, f"{len(errors)} row(s) skipped: {preview}{more}")
        if not success_count and not errors:
            messages.warning(
                self.request,
                "No data rows were found. Double-check the Header Row, Data Start Row and Start Column settings "
                "against your file.",
            )

        return self.redirect_after_upload()

    def redirect_after_upload(self):
        from django.shortcuts import redirect

        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Please choose a valid .xlsx file.")
        return super().form_invalid(form)


class ObjectDeleteView(CrudPermissionMixin, SingleObjectMixin, View):
    """POST-only delete endpoint. The actual "are you sure?" confirmation
    happens client-side via a Bootstrap modal on the list page, so no
    dedicated confirmation template/page is needed per model.
    """

    success_message = "Record deleted successfully."

    def post(self, request, *args, **kwargs):
        from django.db.models import ProtectedError

        obj = self.get_object()
        obj_repr = str(obj)
        try:
            obj.delete()
        except ProtectedError:
            logger.warning("Blocked delete of protected %s '%s' by %s", self.model.__name__, obj_repr, request.user.email)
            messages.error(
                request,
                f"'{obj_repr}' cannot be deleted because other records (e.g. sales data) still reference it. "
                "Remove those references first.",
            )
            return redirect(self.success_url)
        logger.info("%s deleted '%s' by %s", self.model.__name__, obj_repr, request.user.email)
        messages.success(request, self.success_message)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        # Deletion must always be confirmed via modal + POST.
        return redirect(self.success_url)


class BootstrapButtonMixin:
    """No-op marker mixin kept for template convention; buttons are styled in templates."""

    pass

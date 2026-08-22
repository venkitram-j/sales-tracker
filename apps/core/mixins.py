import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView
from django_tables2 import SingleTableMixin

from apps.core.forms import ExcelUploadForm
from apps.core.utils import ExcelParseError, build_data_frame, chunk_dataframe, load_excel

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
    "products.add_product". Superusers, and any user holding the
    permission directly, pass automatically - this is native
    django.contrib.auth behaviour, nothing custom is implemented. Every
    user's permissions are kept in sync with their is_staff flag by
    apps.accounts.signals.sync_user_permissions.
    """

    raise_exception = False  # redirected to login, or show 403 if authenticated but lacking perms

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission to perform this action.")
            return redirect(self.get_permission_denied_redirect())
        return super().handle_no_permission()

    def get_permission_denied_redirect(self):
        return reverse_lazy("dashboard:home")


class FilteredTableListView(SingleTableMixin, CrudPermissionMixin, ListView):
    """Base for every list page: a django-filter FilterSet drives the
    search/filter form, a django-tables2 table drives sortable, paginated
    display. Subclasses set `model`, `table_class`, `filterset_class`,
    `template_name`, `permission_required`, and override `get_base_queryset()`
    (not `get_queryset()`) for any custom starting queryset (e.g.
    `select_related`) - filtering is applied on top of that automatically.
    """

    filterset_class = None

    def get_base_queryset(self):
        return super().get_queryset()

    def get_queryset(self):
        self.filterset = self.filterset_class(self.request.GET, queryset=self.get_base_queryset(), request=self.request)
        return self.filterset.qs

    def get_table_kwargs(self):
        return {"request": self.request}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.filterset
        return ctx


class ExcelUploadView(CrudPermissionMixin, FormView):
    """Generic base view for bulk-creating/updating records from an .xlsx file,
    entirely on top of pandas DataFrames - built for large files (500k+ rows):

    - The workbook is read once with pandas + the calamine engine (a fast
      Rust-based reader, see apps.core.utils.load_excel).
    - Header detection, whitespace stripping, and blank-row removal are
      all vectorized pandas operations (apps.core.utils.build_data_frame)
      rather than a per-row Python loop.
    - The cleaned DataFrame is split into fixed-size chunks
      (apps.core.utils.chunk_dataframe) and each chunk is handed to the
      subclass for database writes, so a 500k-row file becomes ~100
      round trips instead of 500k.

    Subclasses implement:

    - `process_chunk(chunk_df)`: given a DataFrame slice of up to
      `chunk_size` rows, validate/resolve/write it to the database -
      typically via a bulk existence check followed by `bulk_create`/
      `bulk_create(..., update_conflicts=True)` - and return
      (created_count, updated_count, skipped_count, errors), where
      `errors` is a list of human-readable strings for any rows that
      couldn't be applied.
    """

    form_class = ExcelUploadForm
    template_name = "partials/excel_upload_form.html"
    entity_label = "records"
    upload_title = "Bulk Upload"
    expected_columns = []
    upload_help_text = ""
    chunk_size = 5000

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["upload_title"] = self.upload_title
        ctx["expected_columns"] = self.expected_columns
        ctx["upload_help_text"] = self.upload_help_text
        ctx["cancel_url"] = self.success_url
        return ctx

    def before_rows(self, form, raw_df, header_row):
        """Optional hook for subclasses that need to inspect the raw,
        header-less DataFrame (e.g. metadata sitting above the header row)
        before per-chunk processing starts. Raise ValueError with a
        user-facing message to abort the whole upload before any rows are
        processed.
        """
        return None

    def build_dataframe(self, raw_df, header_row, start_col):
        """Transforms the raw, header-less DataFrame into a clean, long
        DataFrame ready for chunking - one row per record, normalized
        column names. Default: delegates to apps.core.utils.build_data_frame
        (a single header row, one column per field - the common case).

        Override for source formats that don't fit that shape - e.g. a
        wide/pivot layout where one dimension is spread across repeated
        column groups instead of a per-row value; see
        apps.sales_data.views.SalesDataExcelUploadView for an example that
        unpivots a "one column-triplet per branch" spreadsheet into a
        normal long DataFrame.
        """
        return build_data_frame(raw_df, header_row=header_row, start_col=start_col)

    def process_chunk(self, chunk_df):
        """Must return (created_count, updated_count, skipped_count, errors)."""
        raise NotImplementedError

    def _fail(self, form, message):
        messages.error(self.request, message)
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["excel_file"]
        header_row = form.cleaned_data["header_row"]
        start_col = form.cleaned_data["start_column_index"]

        try:
            raw_df = load_excel(uploaded_file)
        except ExcelParseError as exc:
            return self._fail(form, str(exc))

        try:
            self.before_rows(form, raw_df, header_row)
        except ValueError as exc:
            return self._fail(form, str(exc))

        try:
            data = self.build_dataframe(raw_df, header_row=header_row, start_col=start_col)
        except ExcelParseError as exc:
            return self._fail(form, str(exc))

        created = updated = skipped = 0
        errors = []

        for chunk in chunk_dataframe(data, self.chunk_size):
            if chunk.empty:
                continue
            try:
                c, u, s, chunk_errors = self.process_chunk(chunk)
                created += c
                updated += u
                skipped += s
                errors.extend(chunk_errors)
            except Exception:  # noqa: BLE001
                logger.exception("Chunk of %s rows failed during bulk insert/update", len(chunk))
                errors.append(f"A batch of {len(chunk)} row(s) failed unexpectedly; see server logs.")

        if created or updated or skipped:
            parts = []
            if created:
                parts.append(f"{created} created")
            if updated:
                parts.append(f"{updated} updated")
            if skipped:
                parts.append(f"{skipped} already existed and were skipped")
            messages.success(self.request, f"Processed {self.entity_label}: {', '.join(parts)}.")
        if errors:
            preview = "; ".join(errors[:10])
            more = f" (+{len(errors) - 10} more)" if len(errors) > 10 else ""
            messages.warning(self.request, f"{len(errors)} row(s) skipped due to errors: {preview}{more}")
        if not created and not updated and not skipped and not errors:
            messages.warning(
                self.request,
                "No data rows were found. Double-check the Header Row and Start Column settings against your file.",
            )

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

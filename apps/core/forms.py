from django import forms


class BootstrapModelForm(forms.ModelForm):
    """Automatically applies Bootstrap classes to every widget.

    Every entity form in the project should extend this instead of
    django.forms.ModelForm so field styling stays consistent and DRY.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            css_class = "form-check-input" if isinstance(widget, forms.CheckboxInput) else "form-select" if isinstance(
                widget, (forms.Select, forms.SelectMultiple)
            ) else "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()
            if isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = "form-control"


class ExcelUploadForm(forms.Form):
    """Generic single-file excel upload form reused by every module.

    Also lets the user tell the parser where the real table actually
    starts, for spreadsheets that have a title banner, notes, or extra
    leading columns before the data - see apps.core.utils.iter_excel_rows.
    """

    excel_file = forms.FileField(
        label="Excel File (.xlsx)",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".xlsx"}),
    )
    header_row = forms.IntegerField(
        label="Header Row",
        initial=1,
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Row number containing the column headers (1 = first row).",
    )
    data_start_row = forms.IntegerField(
        label="Data Start Row",
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Auto (header row + 1)"}),
        help_text="Row number where data begins. Leave blank to use the row right after the header row.",
    )
    start_column = forms.CharField(
        label="Start Column",
        initial="A",
        max_length=3,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "A"}),
        help_text="Column letter where your headers/data begin (e.g. A, B, C). Use this to skip leading columns.",
    )

    def clean_excel_file(self):
        uploaded = self.cleaned_data["excel_file"]
        if not uploaded.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Only .xlsx files are supported.")
        from django.conf import settings

        if uploaded.size > settings.EXCEL_UPLOAD_MAX_SIZE:
            max_mb = settings.EXCEL_UPLOAD_MAX_SIZE / (1024 * 1024)
            raise forms.ValidationError(f"File too large. Maximum allowed size is {max_mb:.0f}MB.")
        return uploaded

    def clean_start_column(self):
        from openpyxl.utils import column_index_from_string
        from openpyxl.utils.exceptions import IllegalCharacterError

        raw = self.cleaned_data["start_column"].strip().upper()
        if not raw.isalpha():
            raise forms.ValidationError("Enter a column letter, e.g. A, B or C.")
        try:
            self.cleaned_data["start_column_index"] = column_index_from_string(raw)
        except (ValueError, IllegalCharacterError):
            raise forms.ValidationError("That doesn't look like a valid column letter.")
        return raw

    def clean(self):
        cleaned_data = super().clean()
        header_row = cleaned_data.get("header_row")
        data_start_row = cleaned_data.get("data_start_row")
        if header_row and data_start_row and data_start_row <= header_row:
            self.add_error("data_start_row", "Data start row must come after the header row.")
        return cleaned_data

from django import forms

from apps.core.forms import BootstrapModelForm

from .models import SalesData


class SalesDataForm(BootstrapModelForm):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = SalesData
        fields = [
            "product_code", "description", "department", "branch", "admin", "buyer",
            "start_date", "end_date", "total_sales_qty", "total_sales_amt", "total_stock",
        ]

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be before the start date.")
        return cleaned_data

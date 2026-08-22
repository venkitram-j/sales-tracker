import django_filters
from django import forms

from apps.branches.models import Branch
from apps.products.models import Product

from .models import SalesData


class SalesDataFilter(django_filters.FilterSet):
    branch = django_filters.ModelChoiceFilter(
        queryset=Branch.objects.filter(is_active=True).order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    product = django_filters.ModelChoiceFilter(
        queryset=Product.objects.filter(is_active=True).order_by("product_code"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    date_from = django_filters.DateFilter(
        field_name="start_date", lookup_expr="gte", label="From",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    date_to = django_filters.DateFilter(
        field_name="end_date", lookup_expr="lte", label="To",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    class Meta:
        model = SalesData
        fields = ["branch", "product", "date_from", "date_to"]

import django_filters
from django import forms

from apps.core.filters import ActiveStatusFilter

from .models import Branch


class BranchFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        field_name="name", lookup_expr="icontains", label="Search",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search by name..."}),
    )
    is_active = ActiveStatusFilter()

    class Meta:
        model = Branch
        fields = ["q", "is_active"]

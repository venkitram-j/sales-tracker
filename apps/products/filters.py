import django_filters
from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.core.filters import ActiveStatusFilter

from .models import Product

User = get_user_model()


class ProductFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method="filter_q", label="Search",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search by product code, description or department..."}),
    )
    admin = django_filters.ModelChoiceFilter(
        queryset=User.objects.order_by("full_name"), widget=forms.Select(attrs={"class": "form-select"}),
    )
    buyer = django_filters.ModelChoiceFilter(
        queryset=User.objects.order_by("full_name"), widget=forms.Select(attrs={"class": "form-select"}),
    )
    is_active = ActiveStatusFilter()

    class Meta:
        model = Product
        fields = ["q", "admin", "buyer", "is_active"]

    def filter_q(self, queryset, name, value):
        return queryset.filter(Q(product_code__icontains=value) | Q(description__icontains=value) | Q(department__icontains=value))

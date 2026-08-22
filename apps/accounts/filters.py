import django_filters
from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.core.filters import ActiveStatusFilter

User = get_user_model()

ROLE_CHOICES = [("true", "Staff"), ("false", "Standard")]


class UserFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method="filter_q", label="Search",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search by name or email..."}),
    )
    is_staff = django_filters.ChoiceFilter(
        choices=ROLE_CHOICES, method="filter_is_staff", label="Role",
        widget=forms.Select(attrs={"class": "form-select"}), empty_label="Staff/Standard",
    )
    is_active = ActiveStatusFilter()

    class Meta:
        model = User
        fields = ["q", "is_staff", "is_active"]

    def filter_q(self, queryset, name, value):
        return queryset.filter(Q(full_name__icontains=value) | Q(email__icontains=value))

    def filter_is_staff(self, queryset, name, value):
        return queryset.filter(is_staff=(value == "true"))

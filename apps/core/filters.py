"""Small filter pieces shared across every app's FilterSet."""
import django_filters
from django import forms

ACTIVE_STATUS_CHOICES = [("true", "Active"), ("false", "Inactive")]


def _filter_active_status(queryset, name, value):
    if not value:
        return queryset
    return queryset.filter(**{name: value == "true"})


class ActiveStatusFilter(django_filters.ChoiceFilter):
    """Reusable "Active/Inactive" status filter - use as
    `is_active = ActiveStatusFilter()` on any FilterSet whose model has
    an `is_active` field (every entity in this app, via TimeStampedModel).
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("choices", ACTIVE_STATUS_CHOICES)
        kwargs.setdefault("label", "Status")
        kwargs.setdefault("empty_label", "Active/Inactive")
        kwargs.setdefault("widget", forms.Select(attrs={"class": "form-select"}))
        kwargs.setdefault("method", _filter_active_status)
        super().__init__(*args, **kwargs)

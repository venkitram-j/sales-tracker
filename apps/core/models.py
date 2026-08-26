from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base class providing self-updating created/updated fields."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Inactive records are hidden from normal operation.")

    class Meta:
        abstract = True

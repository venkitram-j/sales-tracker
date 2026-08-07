from django.db import models

from apps.core.models import TimeStampedModel


class Department(TimeStampedModel):
    """A department that products are categorised under (e.g. Electronics, Grocery)."""

    name = models.CharField(max_length=255, unique=True, db_index=True)
    code = models.CharField("Department Code", max_length=32, unique=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

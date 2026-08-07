from django.db import models

from apps.core.models import TimeStampedModel


class Branch(TimeStampedModel):
    """A physical store location."""

    name = models.CharField(max_length=255, unique=True, db_index=True)
    code = models.CharField("Branch Code", max_length=32, unique=True, db_index=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Branches"

    def __str__(self):
        return f"{self.name} ({self.code})"

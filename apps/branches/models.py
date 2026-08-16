from django.db import models

from apps.core.models import TimeStampedModel


class Branch(TimeStampedModel):
    """A physical store location, identified solely by name."""

    name = models.CharField(max_length=255, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Branches"

    def __str__(self):
        return self.name

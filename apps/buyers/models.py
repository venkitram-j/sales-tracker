from django.db import models

from apps.core.models import TimeStampedModel


class Buyer(TimeStampedModel):
    """A buyer/vendor responsible for procuring products for the store, identified solely by name."""

    name = models.CharField(max_length=255, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

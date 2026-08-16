from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Product(TimeStampedModel):
    """A sellable product managed by the store."""

    product_code = models.CharField("Product Code", max_length=64, unique=True, db_index=True)
    description = models.CharField(max_length=500, blank=True)
    department = models.CharField(max_length=255, blank=True)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="products_administered",
        help_text="User who administers this product.",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="products_bought",
        help_text="User who buys/procures this product.",
    )

    class Meta:
        ordering = ["product_code"]
        indexes = [models.Index(fields=["department"])]

    def __str__(self):
        return self.product_code

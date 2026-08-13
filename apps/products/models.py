from django.db import models

from apps.core.models import TimeStampedModel
from apps.departments.models import Department


class Product(TimeStampedModel):
    """A sellable product managed by the store. Each product belongs to exactly one department."""

    product_code = models.CharField("Product Code", max_length=64, unique=True, db_index=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="products",
        help_text="Department this product belongs to.",
    )

    class Meta:
        ordering = ["product_code"]
        indexes = [models.Index(fields=["department"])]

    def __str__(self):
        return self.product_code

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.departments.models import Department


class Product(TimeStampedModel):
    """A sellable product managed by the store. Each product belongs to exactly one department."""

    name = models.CharField(max_length=255, unique=True, db_index=True)
    sku = models.CharField("SKU / Product Code", max_length=64, unique=True, db_index=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="products",
        help_text="Department this product belongs to.",
    )
    category = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)],
        help_text="Standard selling price per unit.",
    )

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name", "sku"]), models.Index(fields=["department"])]

    def __str__(self):
        return f"{self.name} ({self.sku})"

from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import Product


class Buyer(TimeStampedModel):
    """A buyer/vendor responsible for procuring products for the store."""

    name = models.CharField(max_length=255, db_index=True)
    company = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    products = models.ManyToManyField(Product, related_name="buyers", blank=True, help_text="Products this buyer procures.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}" + (f" - {self.company}" if self.company else "")

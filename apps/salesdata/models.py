from django.core.validators import MinValueValidator
from django.db import models

from apps.branches.models import Branch
from apps.buyers.models import Buyer
from apps.core.models import TimeStampedModel
from apps.departments.models import Department
from apps.products.models import Product
from apps.store_admins.models import StoreAdmin


class SalesData(TimeStampedModel):
    """A single sales/stock-period record for a product at a branch."""

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sales_records")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="sales_records")
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="sales_records",
        help_text="Defaults to the product's department when left blank.",
    )
    admin = models.ForeignKey(
        StoreAdmin, on_delete=models.PROTECT, related_name="sales_records",
        help_text="Store admin who recorded/manages this sale.",
    )
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT, related_name="sales_records")
    sales_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    sales_value = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    total_stock = models.PositiveIntegerField(help_text="Total stock on hand for this product/branch during the reporting period.")
    start_date = models.DateField(db_index=True, help_text="Start of the reporting period.")
    end_date = models.DateField(db_index=True, help_text="End of the reporting period.")

    class Meta:
        ordering = ["-start_date", "-created_at"]
        verbose_name = "Sales Data"
        verbose_name_plural = "Sales Data"
        indexes = [
            models.Index(fields=["branch", "product", "start_date"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["department"]),
        ]

    def __str__(self):
        return f"{self.product.name} @ {self.branch.name} ({self.start_date} to {self.end_date})"

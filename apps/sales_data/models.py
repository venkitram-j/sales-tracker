from django.db import models

from apps.branches.models import Branch
from apps.core.models import TimeStampedModel
from apps.products.models import Product


class SalesData(TimeStampedModel):
    """A single sales/stock-period record for a product at a branch.

    Uniquely identified by (product, branch, start_date, end_date):
    uploading a row for a combination that already exists replaces it
    rather than creating a duplicate - see apps.sales_data.views for the
    upload logic that relies on the matching UniqueConstraint below.

    Quantities/amounts are plain (signed) fields rather than
    positive-only: real source data includes negative values for
    returns/adjustments, so a non-negative constraint would incorrectly
    reject legitimate rows.
    """

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sales_records")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="sales_records")
    start_date = models.DateField(db_index=True, help_text="Start of the reporting period.")
    end_date = models.DateField(db_index=True, help_text="End of the reporting period.")
    total_sales_qty = models.IntegerField()
    total_sales_amt = models.DecimalField(max_digits=14, decimal_places=2)
    total_stock = models.IntegerField(help_text="Total stock on hand for this product/branch during the reporting period.")

    class Meta:
        ordering = ["-start_date", "-created_at"]
        verbose_name = "Sales Data"
        verbose_name_plural = "Sales Data"
        indexes = [
            models.Index(fields=["branch", "product", "start_date"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "branch", "start_date", "end_date"],
                name="unique_sales_data_product_branch_period",
            )
        ]

    def __str__(self):
        return f"{self.product} @ {self.branch} ({self.start_date} to {self.end_date})"

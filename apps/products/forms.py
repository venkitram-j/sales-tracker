from apps.core.forms import BootstrapModelForm

from .models import Product


class ProductForm(BootstrapModelForm):
    class Meta:
        model = Product
        fields = ["name", "sku", "department", "category", "description", "unit_price", "is_active"]

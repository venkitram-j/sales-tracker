from apps.core.forms import BootstrapModelForm

from .models import Product


class ProductForm(BootstrapModelForm):
    class Meta:
        model = Product
        fields = ["product_code", "description", "department", "is_active"]

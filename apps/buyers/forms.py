from django.forms import SelectMultiple

from apps.core.forms import BootstrapModelForm

from .models import Buyer


class BuyerForm(BootstrapModelForm):
    class Meta:
        model = Buyer
        fields = ["name", "company", "email", "phone", "address", "products", "is_active"]
        widgets = {
            "products": SelectMultiple(attrs={"size": 6}),
        }

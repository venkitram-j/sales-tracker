from apps.core.forms import BootstrapModelForm

from .models import Buyer


class BuyerForm(BootstrapModelForm):
    class Meta:
        model = Buyer
        fields = ["name", "is_active"]

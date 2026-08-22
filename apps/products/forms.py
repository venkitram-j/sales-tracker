from django.contrib.auth import get_user_model

from apps.core.forms import BootstrapModelForm

from .models import Product

User = get_user_model()


class ProductForm(BootstrapModelForm):
    class Meta:
        model = Product
        fields = ["product_code", "description", "department", "admin", "buyer", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_qs = User.objects.filter(is_active=True).order_by("full_name")
        for field_name in ("admin", "buyer"):
            self.fields[field_name].queryset = user_qs
            self.fields[field_name].label_from_instance = lambda u: u.full_name or u.email

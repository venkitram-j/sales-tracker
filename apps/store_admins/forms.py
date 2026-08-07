from django.contrib.auth import get_user_model
from django.db.models import Q
from django.forms import SelectMultiple

from apps.core.forms import BootstrapModelForm

from .models import StoreAdmin

User = get_user_model()


class StoreAdminForm(BootstrapModelForm):
    class Meta:
        model = StoreAdmin
        fields = ["user", "branches", "phone", "is_active"]
        widgets = {
            "branches": SelectMultiple(attrs={"size": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        if self.instance and self.instance.pk:
            qs = qs.filter(Q(store_admin_profile__isnull=True) | Q(pk=self.instance.user_id))
        else:
            qs = qs.filter(store_admin_profile__isnull=True)
        self.fields["user"].queryset = qs
        self.fields["user"].label_from_instance = lambda u: f"{u.get_full_name() or u.email} <{u.email}>"

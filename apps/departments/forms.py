from apps.core.forms import BootstrapModelForm

from .models import Department


class DepartmentForm(BootstrapModelForm):
    class Meta:
        model = Department
        fields = ["name", "is_active"]

from apps.core.forms import BootstrapModelForm

from .models import Branch


class BranchForm(BootstrapModelForm):
    class Meta:
        model = Branch
        fields = ["name", "code", "city", "state", "address", "is_active"]

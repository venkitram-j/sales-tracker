from apps.core.forms import BootstrapModelForm

from .models import Branch


class BranchForm(BootstrapModelForm):
    class Meta:
        model = Branch
        fields = ["name", "is_active"]

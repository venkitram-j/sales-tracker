from django.contrib.auth import get_user_model
from django.db import models

from apps.branches.models import Branch
from apps.core.models import TimeStampedModel

User = get_user_model()


class StoreAdmin(TimeStampedModel):
    """A regular Django User who has been designated to manage one or more branches.

    User accounts themselves are created only via the Django admin panel;
    this model simply attaches branch-management responsibility to an
    existing user.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="store_admin_profile")
    branches = models.ManyToManyField(Branch, related_name="store_admins", blank=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]
        verbose_name = "Store Admin"
        verbose_name_plural = "Store Admins"

    def __str__(self):
        return self.user.get_full_name() or self.user.email

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.email

    @property
    def branch_list(self):
        return ", ".join(self.branches.values_list("name", flat=True))

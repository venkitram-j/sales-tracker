from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Built-in Django auth User, extended with a real (not computed-on-read)
    full_name column - kept in sync with first_name/last_name by the
    pre_save signal in apps.accounts.signals, alongside the same signal's
    existing email->username sync. A real field (rather than a property)
    is what makes it usable for sorting/filtering (django-tables2,
    django-filter) and for the simple, direct lookups the Product Excel
    upload needs when resolving Admin/Buyer by name.
    """

    full_name = models.CharField(max_length=255, blank=True, db_index=True)

    def __str__(self):
        return self.full_name or self.email

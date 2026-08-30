"""
User models
"""

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Built-in Django auth User, extended with pre-computed full_name field
    for filtering purposes. Populated via signals.
    """

    full_name = models.CharField(max_length=255, blank=True, unique=True, db_index=True)

    def __str__(self):
        return self.full_name or self.email

    def user_initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}".upper()

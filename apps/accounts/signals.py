"""
User model signals
"""

from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(pre_save, sender=User)
def sync_derived_fields(sender, instance, **kwargs):
    """
    Auto populate username and full_name field before saving object.
    """
    if instance.email:
        instance.email = instance.email.strip().lower()
        instance.username = instance.email
    instance.full_name = f"{instance.first_name} {instance.last_name}".strip()

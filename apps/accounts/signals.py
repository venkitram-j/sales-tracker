import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.dispatch import receiver

logger = logging.getLogger("apps.accounts")

User = get_user_model()


@receiver(pre_save, sender=User)
def sync_username_with_email(sender, instance, **kwargs):
    """Username is a required, unique field on the built-in User model.

    Rather than swapping in a custom user model, we keep the app entirely
    on `django.contrib.auth.models.User` (as required) and simply mirror
    the email address into `username` automatically. Admin-panel forms
    hide the username field, so staff never interact with it directly.
    """
    if instance.email:
        instance.email = instance.email.strip().lower()
        instance.username = instance.email

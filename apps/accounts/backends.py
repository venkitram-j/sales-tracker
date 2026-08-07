import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger("apps.accounts")

User = get_user_model()


class EmailBackend(ModelBackend):
    """Authenticates users against their email address instead of username.

    Uses the built-in django.contrib.auth.models.User as-is; the
    `username` field is populated automatically (see signals.py) so it
    never needs to be surfaced to end users.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            # Run the default hasher regardless, to mitigate user enumeration
            # via response-time differences.
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            logger.error("Multiple users share the email %s", email)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

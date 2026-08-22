import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger("apps.accounts")

User = get_user_model()

# Every user (staff or not) gets full CRUD on the app's core entities;
# staff additionally get user-management permissions. This is the single
# place that encodes the "normal vs staff" permission model - deliberately
# simple (direct user_permissions, no Groups), since a user's permissions
# are fully determined by their is_staff flag alone.
ENTITY_PERMISSION_CODENAMES = [
    "view_branch", "add_branch", "change_branch", "delete_branch",
    "view_product", "add_product", "change_product", "delete_product",
    "view_salesdata", "add_salesdata", "change_salesdata", "delete_salesdata",
]
STAFF_ONLY_PERMISSION_CODENAMES = ["view_user", "add_user", "change_user"]


@receiver(pre_save, sender=User)
def sync_derived_fields(sender, instance, **kwargs):
    """Username is a required, unique field on AbstractUser - mirror the
    email into it so it never needs manual entry. full_name is likewise
    kept as a real, queryable/sortable column (not a computed property),
    synced here from first_name/last_name.
    """
    if instance.email:
        instance.email = instance.email.strip().lower()
        instance.username = instance.email
    instance.full_name = f"{instance.first_name} {instance.last_name}".strip()


@receiver(post_save, sender=User)
def sync_user_permissions(sender, instance, **kwargs):
    """Keeps every user's permissions in lockstep with their is_staff flag:
    everyone gets full CRUD on Branches/Products/Sales Data; staff
    additionally get User management permissions. Runs after every save
    (admin panel, the app's own user forms, management commands) so
    permissions never drift out of sync with is_staff. Superusers bypass
    permission checks entirely regardless (standard Django behaviour), so
    this is harmless for them too.
    """
    codenames = ENTITY_PERMISSION_CODENAMES + (STAFF_ONLY_PERMISSION_CODENAMES if instance.is_staff else [])
    instance.user_permissions.set(Permission.objects.filter(codename__in=codenames))

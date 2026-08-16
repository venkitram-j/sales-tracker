"""
Creates a standard set of permission Groups using Django's built-in
auth permission framework, so new users can be assigned sensible
access levels from the admin panel without hand-picking permissions.

Usage:
    python manage.py seed_groups
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

# app_label.codename per built-in Django convention (add_/change_/delete_/view_ + model name)
GROUP_DEFINITIONS = {
    "Viewer": [
        "products.view_product",
        "branches.view_branch",
        "sales_data.view_salesdata",
    ],
    "Branch Manager": [
        "products.view_product",
        "branches.view_branch",
        "sales_data.view_salesdata", "sales_data.add_salesdata", "sales_data.change_salesdata",
    ],
    "Data Administrator": [
        "products.view_product", "products.add_product", "products.change_product", "products.delete_product",
        "branches.view_branch", "branches.add_branch", "branches.change_branch", "branches.delete_branch",
        "sales_data.view_salesdata", "sales_data.add_salesdata", "sales_data.change_salesdata", "sales_data.delete_salesdata",
    ],
}


class Command(BaseCommand):
    help = "Creates/updates the standard Viewer, Branch Manager and Data Administrator permission groups."

    def handle(self, *args, **options):
        for group_name, codenames in GROUP_DEFINITIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            permissions = []
            missing = []
            for full_codename in codenames:
                app_label, codename = full_codename.split(".")
                try:
                    permissions.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
                except Permission.DoesNotExist:
                    missing.append(full_codename)
            group.permissions.set(permissions)
            status = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{status} group '{group_name}' with {len(permissions)} permission(s)."))
            if missing:
                self.stdout.write(self.style.WARNING(f"  Skipped unknown permissions: {', '.join(missing)}"))

        self.stdout.write(self.style.SUCCESS("Done. Assign users to these groups via the admin panel (Users > Permissions)."))

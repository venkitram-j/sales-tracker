"""
Creates Django Users from a list of full names, for local development
only. Emails are generated from the full name (e.g. "Alice Admin" ->
alice.admin@example.com) and every user gets the same password, purely
for convenience when seeding a dev database - never use this in
production.

Usage:
    python manage.py create_dev_users "Alice Admin" "Bob Manager"
    python manage.py create_dev_users --file names.txt
    python manage.py create_dev_users "Alice Admin" --password "MyDevPass123!" --domain example.com
    python manage.py create_dev_users "Alice Admin" --superuser
"""
import re
import unicodedata

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()

DEFAULT_DEV_PASSWORD = "DevPass123!"


def slugify_name_part(part):
    """ASCII-folds and strips a name part down to lowercase letters/digits only."""
    normalized = unicodedata.normalize("NFKD", part).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", normalized.lower())


def email_from_full_name(full_name, domain):
    parts = [slugify_name_part(p) for p in full_name.split() if slugify_name_part(p)]
    if not parts:
        return None
    return f"{'.'.join(parts)}@{domain}"


class Command(BaseCommand):
    help = "Dev-only: creates Users from a list of full names, with emails generated as first.last@<domain> and a shared password."

    def add_arguments(self, parser):
        parser.add_argument("names", nargs="*", help="Full names to create, e.g. \"Alice Admin\" \"Bob Manager\"")
        parser.add_argument("--file", help="Path to a text file with one full name per line (blank lines ignored).")
        parser.add_argument("--domain", default="example.com", help="Email domain to use (default: example.com).")
        parser.add_argument("--password", default=DEFAULT_DEV_PASSWORD, help=f"Shared password for every created user (default: {DEFAULT_DEV_PASSWORD}).")
        parser.add_argument("--superuser", action="store_true", help="Also make every created user a superuser.")
        parser.add_argument("--staff", action="store_true", help="Also make every created user staff (can log into /admin/).")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "This command is for local development only and refuses to run with DEBUG=False. "
                "Create users via the admin panel in production."
            )

        names = list(options["names"])
        if options.get("file"):
            with open(options["file"], encoding="utf-8") as fh:
                names.extend(line.strip() for line in fh if line.strip())

        if not names:
            raise CommandError("Provide at least one full name as an argument, or --file <path>.")

        domain = options["domain"]
        password = options["password"]
        is_superuser = options["superuser"]
        is_staff = options["staff"] or is_superuser

        created, skipped = 0, 0
        for full_name in names:
            full_name = full_name.strip()
            if not full_name:
                continue
            parts = full_name.split(maxsplit=1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

            email = email_from_full_name(full_name, domain)
            if not email:
                self.stdout.write(self.style.WARNING(f"Skipped '{full_name}': could not derive an email from it."))
                skipped += 1
                continue

            if User.objects.filter(email__iexact=email).exists():
                self.stdout.write(self.style.WARNING(f"Skipped '{full_name}': a user with email {email} already exists."))
                skipped += 1
                continue

            User.objects.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name,
                is_staff=is_staff, is_superuser=is_superuser,
            )
            self.stdout.write(self.style.SUCCESS(f"Created {full_name} <{email}>"))
            created += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone: {created} user(s) created, {skipped} skipped."))
        if created:
            self.stdout.write(f"Shared password for all created users: {password}")

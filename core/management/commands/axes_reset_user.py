"""Reset django-axes lockout records for a user."""

from __future__ import annotations

from axes.utils import reset
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Clear django-axes access attempts for a user email (unlock account)."

    def add_arguments(self, parser):
        parser.add_argument("email", help="User email (USERNAME_FIELD).")

    def handle(self, *args, **options):
        email = (options["email"] or "").strip().lower()
        if not email:
            raise CommandError("Email is required.")

        user_model = get_user_model()
        if not user_model.objects.filter(email=email).exists():
            raise CommandError(f"No user with email: {email}")

        removed = reset(username=email)
        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {removed} access attempt record(s) for {email}."
            )
        )

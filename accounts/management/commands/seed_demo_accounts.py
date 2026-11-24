from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AccountProfile
from catalog.models import Merchant


class Command(BaseCommand):
    help = "Create local demo accounts for the seeded catalog."

    def handle(self, *args, **options):
        user_model = get_user_model()
        credentials = []
        with transaction.atomic():
            try:
                merchant = Merchant.objects.get(slug="verde-kitchen")
            except Merchant.DoesNotExist as error:
                raise CommandError("Run seed_demo before seeding demo accounts.") from error

            demo_accounts = (
                ("demo-customer", AccountProfile.Role.CUSTOMER, None),
                ("demo-merchant", AccountProfile.Role.MERCHANT, merchant),
            )
            for username, role, associated_merchant in demo_accounts:
                user, created = user_model.objects.get_or_create(username=username)
                if not created:
                    if not AccountProfile.objects.filter(
                        user=user, role=role, merchant=associated_merchant
                    ).exists():
                        raise CommandError(
                            f"The account {username} already exists with a different profile."
                        )
                    continue

                password = token_urlsafe(18)
                user.set_password(password)
                user.save(update_fields=["password"])
                AccountProfile.objects.create(
                    user=user, role=role, merchant=associated_merchant
                )
                credentials.append((username, password))

        if not credentials:
            self.stdout.write("Demo accounts already exist. Passwords are unchanged.")
        for username, password in credentials:
            self.stdout.write(f"{username} password: {password}")

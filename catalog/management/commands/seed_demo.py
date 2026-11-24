from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Merchant, Product


class Command(BaseCommand):
    help = "Create demo catalog records that are missing."

    @transaction.atomic
    def handle(self, *args, **options):
        merchant, _ = Merchant.objects.get_or_create(
            slug="verde-kitchen", defaults={"name": "Verde Kitchen"}
        )
        demo_products = (
            ("roast-chicken-bowl", "Roast Chicken Bowl", 1250),
            ("roasted-vegetable-wrap", "Roasted Vegetable Wrap", 975),
            ("lime-sparkling-water", "Lime Sparkling Water", 250),
        )
        created_count = 0
        for slug, name, unit_price_cents in demo_products:
            _, created = Product.objects.get_or_create(
                merchant=merchant,
                slug=slug,
                defaults={"name": name, "unit_price_cents": unit_price_cents},
            )
            created_count += created

        self.stdout.write(f"Demo catalog ready. Products added: {created_count}.")

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Merchant, Product


class CatalogTests(TestCase):
    def test_available_products_show_with_merchant_and_price(self):
        merchant = Merchant.objects.create(name="Example Kitchen", slug="example-kitchen")
        Product.objects.create(
            merchant=merchant, name="Lunch Bowl", slug="lunch-bowl", unit_price_cents=1250
        )
        Product.objects.create(
            merchant=merchant,
            name="Sold-out Wrap",
            slug="sold-out-wrap",
            unit_price_cents=975,
            is_available=False,
        )

        response = self.client.get(reverse("catalog"))

        self.assertContains(response, "Example Kitchen")
        self.assertContains(response, "Lunch Bowl")
        self.assertContains(response, "$12.50")
        self.assertNotContains(response, "Sold-out Wrap")

    def test_empty_catalog(self):
        response = self.client.get(reverse("catalog"))

        self.assertContains(response, "No products are available right now.")


class SeedDemoTests(TestCase):
    def test_repeat_seed_preserves_records_and_changes(self):
        call_command("seed_demo", stdout=StringIO())

        merchant = Merchant.objects.get()
        product_ids = set(merchant.products.values_list("id", flat=True))
        self.assertEqual(len(product_ids), 3)
        product = merchant.products.get(slug="roast-chicken-bowl")
        product.unit_price_cents = 1300
        product.is_available = False
        product.save()

        call_command("seed_demo", stdout=StringIO())

        self.assertEqual(Merchant.objects.get(), merchant)
        self.assertEqual(set(Product.objects.values_list("id", flat=True)), product_ids)
        product.refresh_from_db()
        self.assertEqual(product.unit_price_cents, 1300)
        self.assertFalse(product.is_available)

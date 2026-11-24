from decimal import Decimal

from django.db import models


class Merchant(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField()
    unit_price_cents = models.PositiveIntegerField()
    is_available = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "slug"], name="catalog_product_merchant_slug_unique"
            )
        ]

    def __str__(self):
        return self.name

    @property
    def unit_price(self):
        return Decimal(self.unit_price_cents).scaleb(-2)

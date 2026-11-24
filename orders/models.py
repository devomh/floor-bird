from decimal import Decimal

from django.conf import settings
from django.db import models


class Order(models.Model):
    class State(models.TextChoices):
        PLACED = "placed", "Placed"
        ACCEPTED = "accepted", "Accepted"
        READY = "ready", "Ready"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    merchant = models.ForeignKey(
        "catalog.Merchant", on_delete=models.PROTECT, related_name="orders"
    )
    delivery_address = models.CharField(max_length=500)
    total_cents = models.PositiveBigIntegerField()
    is_payment_simulated = models.BooleanField(default=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PLACED)
    submission_key = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "submission_key"], name="orders_customer_submission_unique"
            )
        ]

    @property
    def total(self):
        return Decimal(self.total_cents).scaleb(-2)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    product_name = models.CharField(max_length=120)
    unit_price_cents = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="orders_item_quantity_positive"
            ),
            models.UniqueConstraint(fields=["order", "product"], name="orders_item_product_unique"),
        ]
        ordering = ["id"]

    @property
    def unit_price(self):
        return Decimal(self.unit_price_cents).scaleb(-2)


class OrderStatusEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    from_state = models.CharField(max_length=16, choices=Order.State.choices, blank=True)
    to_state = models.CharField(max_length=16, choices=Order.State.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

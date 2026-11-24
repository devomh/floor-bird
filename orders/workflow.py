from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from accounts.roles import get_merchant_for_user, is_customer
from catalog.models import Product

from .models import Order, OrderItem, OrderStatusEvent


@transaction.atomic
def place_order(*, customer, merchant, delivery_address, submission_key, quantities):
    if not is_customer(customer):
        raise PermissionDenied
    if (
        not delivery_address
        or not quantities
        or any(quantity <= 0 for quantity in quantities.values())
    ):
        raise ValidationError("Enter a delivery address and choose at least one product.")

    # A per-customer lock serializes concurrent submissions before checking the unique key.
    get_user_model().objects.select_for_update().only("id").get(pk=customer.pk)
    existing = Order.objects.filter(customer=customer, submission_key=submission_key).first()
    if existing is not None:
        saved_quantities = dict(existing.items.values_list("product_id", "quantity"))
        if (
            existing.merchant_id != merchant.pk
            or existing.delivery_address != delivery_address
            or saved_quantities != quantities
        ):
            raise ValidationError("This checkout was already submitted with different details.")
        return existing

    products = list(
        Product.objects.select_for_update()
        .filter(merchant=merchant, is_available=True, pk__in=quantities)
        .order_by("pk")
    )
    if len(products) != len(quantities):
        raise ValidationError("Select available products from this merchant's catalog.")
    total_cents = sum(product.unit_price_cents * quantities[product.pk] for product in products)
    if total_cents > 2**63 - 1:
        raise ValidationError("Reduce the quantities to place this order.")
    order = Order.objects.create(
        customer=customer,
        merchant=merchant,
        delivery_address=delivery_address,
        total_cents=total_cents,
        submission_key=submission_key,
    )
    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            product=product,
            product_name=product.name,
            unit_price_cents=product.unit_price_cents,
            quantity=quantities[product.pk],
        )
        for product in products
    )
    OrderStatusEvent.objects.create(order=order, actor=customer, to_state=Order.State.PLACED)
    return order


@transaction.atomic
def advance_order(*, actor, order_id, target_state):
    merchant = get_merchant_for_user(actor)
    if merchant is None:
        raise PermissionDenied

    order = Order.objects.select_for_update().get(pk=order_id, merchant=merchant)
    required_state = {
        Order.State.ACCEPTED: Order.State.PLACED,
        Order.State.READY: Order.State.ACCEPTED,
    }.get(target_state)
    if order.state != required_state:
        raise ValidationError(f"Order #{order.pk} is currently {order.get_state_display()}.")

    previous_state = order.state
    order.state = target_state
    order.save(update_fields=["state"])
    OrderStatusEvent.objects.create(
        order=order, actor=actor, from_state=previous_state, to_state=target_state
    )

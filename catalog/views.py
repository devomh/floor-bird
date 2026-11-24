from django.shortcuts import render
from django.views.decorators.http import require_safe

from accounts.roles import get_merchant_for_user, is_customer

from .models import Product


@require_safe
def catalog(request):
    products = (
        Product.objects.filter(is_available=True)
        .select_related("merchant")
        .order_by("merchant__name", "merchant_id", "name", "id")
    )
    return render(
        request,
        "catalog/index.html",
        {
            "products": products,
            "can_order": not request.user.is_authenticated or is_customer(request.user),
            "has_merchant_queue": get_merchant_for_user(request.user) is not None,
        },
    )

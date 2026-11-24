from django.shortcuts import render
from django.views.decorators.http import require_safe

from .models import Product


@require_safe
def catalog(request):
    products = (
        Product.objects.filter(is_available=True)
        .select_related("merchant")
        .order_by("merchant__name", "merchant_id", "name", "id")
    )
    return render(request, "catalog/index.html", {"products": products})

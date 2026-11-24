from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from accounts.roles import get_merchant_for_user, is_customer
from catalog.models import Merchant

from .forms import CheckoutForm
from .models import Order
from .workflow import advance_order, place_order


@require_http_methods(["GET", "HEAD", "POST"])
@login_required
def checkout(request, merchant_slug):
    if not is_customer(request.user):
        raise PermissionDenied
    merchant = get_object_or_404(Merchant, slug=merchant_slug)
    products = list(merchant.products.filter(is_available=True).order_by("name", "pk"))
    if request.method == "POST":
        form = CheckoutForm(products, request.POST)
        if form.is_valid():
            try:
                order = place_order(
                    customer=request.user,
                    merchant=merchant,
                    delivery_address=form.cleaned_data["delivery_address"],
                    submission_key=form.cleaned_data["submission_key"],
                    quantities=form.cleaned_data["quantities"],
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                return redirect("orders:detail", order_id=order.pk)
    else:
        form = CheckoutForm(products, initial={"submission_key": uuid4()})
    return render(
        request,
        "orders/checkout.html",
        {"merchant": merchant, "form": form, "quantity_fields": form.quantity_fields},
    )


@require_safe
@login_required
def detail(request, order_id):
    if not is_customer(request.user):
        raise PermissionDenied
    order = get_object_or_404(
        Order.objects.select_related("merchant"), pk=order_id, customer=request.user
    )
    return render(
        request,
        "orders/detail.html",
        {"order": order, "items": order.items.all(), "events": order.events.all()},
    )


@require_safe
@login_required
def merchant_queue(request):
    merchant = get_merchant_for_user(request.user)
    if merchant is None:
        raise PermissionDenied
    orders = merchant.orders.prefetch_related("items").order_by("-pk")
    return render(request, "orders/merchant_queue.html", {"merchant": merchant, "orders": orders})


def _merchant_transition(request, order_id, target_state):
    try:
        advance_order(actor=request.user, order_id=order_id, target_state=target_state)
    except Order.DoesNotExist:
        raise Http404("Order not found.") from None
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, f"Order #{order_id} is now {target_state.label}.")
    return redirect("orders:merchant_queue")


@require_POST
@login_required
def merchant_accept(request, order_id):
    return _merchant_transition(request, order_id, Order.State.ACCEPTED)


@require_POST
@login_required
def merchant_ready(request, order_id):
    return _merchant_transition(request, order_id, Order.State.READY)

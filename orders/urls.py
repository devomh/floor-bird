from django.urls import path

from . import views


app_name = "orders"

urlpatterns = [
    path("merchants/<slug:merchant_slug>/order/", views.checkout, name="checkout"),
    path("orders/<int:order_id>/", views.detail, name="detail"),
    path("merchant/orders/", views.merchant_queue, name="merchant_queue"),
    path("merchant/orders/<int:order_id>/accept/", views.merchant_accept, name="merchant_accept"),
    path("merchant/orders/<int:order_id>/ready/", views.merchant_ready, name="merchant_ready"),
]

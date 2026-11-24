from django.urls import include, path

from catalog.views import catalog

urlpatterns = [
    path("", catalog, name="catalog"),
    path("accounts/", include("accounts.urls")),
    path("", include("orders.urls")),
]

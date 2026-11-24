from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from accounts.models import AccountProfile
from catalog.models import Merchant, Product

from .models import Order, OrderStatusEvent
from .workflow import place_order


ADDRESS = "42 Example Lane, Demo City"


def create_account(username, role, merchant=None):
    user = get_user_model().objects.create_user(username=username)
    AccountProfile.objects.create(user=user, role=role, merchant=merchant)
    return user


def create_product(merchant):
    return Product.objects.create(
        merchant=merchant, name="Lunch Bowl", slug="lunch-bowl", unit_price_cents=1250
    )


class OrderFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.merchant = Merchant.objects.create(name="Example Kitchen", slug="example-kitchen")
        cls.product = create_product(cls.merchant)
        cls.other_merchant = Merchant.objects.create(name="Other Kitchen", slug="other-kitchen")
        cls.other_product = create_product(cls.other_merchant)
        cls.customer = create_account("customer", AccountProfile.Role.CUSTOMER)
        cls.merchant_user = create_account("merchant", AccountProfile.Role.MERCHANT, cls.merchant)

    def setUp(self):
        self.checkout_url = reverse("orders:checkout", args=[self.merchant.slug])
        self.customer_client = Client()
        self.customer_client.force_login(self.customer)
        self.merchant_client = Client()
        self.merchant_client.force_login(self.merchant_user)

    def checkout_payload(self, **overrides):
        return {
            "submission_key": str(uuid4()),
            "delivery_address": ADDRESS,
            f"quantity_{self.product.pk}": "2",
            **overrides,
        }

    def test_browser_routes_place_accept_and_mark_order_ready(self):
        checkout_page = self.customer_client.get(self.checkout_url)
        self.assertContains(checkout_page, self.product.name)
        response = self.customer_client.post(
            self.checkout_url,
            self.checkout_payload(submission_key=checkout_page.context["form"]["submission_key"].value()),
        )
        order = Order.objects.get()
        detail_url = reverse("orders:detail", args=[order.pk])
        queue_url = reverse("orders:merchant_queue")
        self.assertRedirects(response, detail_url)
        self.assertEqual(order.total_cents, 2500)
        self.assertTrue(order.is_payment_simulated)

        queue = self.merchant_client.get(queue_url)
        self.assertContains(queue, self.product.name)
        self.assertNotContains(queue, ADDRESS)
        self.assertRedirects(
            self.merchant_client.post(reverse("orders:merchant_accept", args=[order.pk])), queue_url
        )
        self.assertRedirects(
            self.merchant_client.post(reverse("orders:merchant_ready", args=[order.pk])), queue_url
        )
        order.refresh_from_db()
        self.assertEqual(order.state, Order.State.READY)
        self.assertEqual(
            list(order.events.values_list("from_state", "to_state", "actor_id")),
            [
                ("", "placed", self.customer.pk),
                ("placed", "accepted", self.merchant_user.pk),
                ("accepted", "ready", self.merchant_user.pk),
            ],
        )
        detail = self.customer_client.get(detail_url)
        self.assertContains(detail, ADDRESS)
        self.assertContains(detail, "Ready")

    def test_retry_uses_original_order_and_price_snapshot(self):
        payload = self.checkout_payload()
        original = self.customer_client.post(self.checkout_url, payload)
        self.product.name = "Updated Lunch Bowl"
        self.product.unit_price_cents = 9999
        self.product.is_available = False
        self.product.save()

        retry = self.customer_client.post(self.checkout_url, payload)
        self.assertEqual(original["Location"], retry["Location"])
        order = Order.objects.get()
        self.assertEqual(order.total_cents, 2500)
        self.assertEqual(order.items.get().unit_price_cents, 1250)
        self.assertEqual(order.items.get().product_name, "Lunch Bowl")
        self.assertEqual(order.events.count(), 1)
        self.assertContains(self.customer_client.get(retry["Location"]), "$25.00")

        for changed in (
            {"delivery_address": "Another address"},
            {f"quantity_{self.product.pk}": "1"},
        ):
            with self.subTest(changed=changed):
                response = self.customer_client.post(self.checkout_url, payload | changed)
                self.assertContains(response, "already submitted with different details")
        self.assertEqual(Order.objects.count(), 1)

    def test_invalid_selection_or_missing_address_creates_no_order(self):
        unavailable = Product.objects.create(
            merchant=self.merchant, name="Soup", slug="soup", unit_price_cents=700, is_available=False
        )
        for invalid_fields in (
            {"delivery_address": ""},
            {f"quantity_{self.product.pk}": "-1"},
            {f"quantity_{self.product.pk}": "1.5"},
            {f"quantity_{self.product.pk}": "0"},
            {f"quantity_{unavailable.pk}": "1"},
            {f"quantity_{self.other_product.pk}": "1"},
        ):
            with self.subTest(fields=invalid_fields):
                response = self.customer_client.post(
                    self.checkout_url, self.checkout_payload(**invalid_fields)
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderStatusEvent.objects.exists())

    def test_order_access_is_scoped_to_own_customer_and_merchant(self):
        self.customer_client.post(self.checkout_url, self.checkout_payload())
        order = Order.objects.get()
        detail_url = reverse("orders:detail", args=[order.pk])
        accept_url = reverse("orders:merchant_accept", args=[order.pk])
        queue_url = reverse("orders:merchant_queue")
        outsider = Client()
        self.assertRedirects(
            outsider.get(self.checkout_url),
            f"{reverse('accounts:login')}?next={self.checkout_url}",
        )
        outsider.force_login(create_account("other-customer", AccountProfile.Role.CUSTOMER))
        self.assertEqual(outsider.get(detail_url).status_code, 404)
        self.assertEqual(outsider.post(accept_url).status_code, 403)
        self.assertEqual(outsider.get(queue_url).status_code, 403)
        outsider.force_login(
            create_account("other-merchant", AccountProfile.Role.MERCHANT, self.other_merchant)
        )
        self.assertEqual(outsider.get(detail_url).status_code, 403)
        self.assertNotContains(outsider.get(queue_url), self.product.name)
        self.assertEqual(outsider.post(accept_url).status_code, 404)
        self.assertEqual(
            self.merchant_client.post(self.checkout_url, self.checkout_payload()).status_code,
            403,
        )
        self.assertEqual(order.events.count(), 1)

    def test_stale_or_out_of_order_transition_creates_no_event(self):
        self.customer_client.post(self.checkout_url, self.checkout_payload())
        order = Order.objects.get()
        ready_url = reverse("orders:merchant_ready", args=[order.pk])
        accept_url = reverse("orders:merchant_accept", args=[order.pk])

        response = self.merchant_client.post(ready_url, follow=True)
        self.assertContains(response, "currently Placed")
        order.refresh_from_db()
        self.assertEqual(order.state, Order.State.PLACED)
        self.assertEqual(order.events.count(), 1)

        self.merchant_client.post(accept_url)
        response = self.merchant_client.post(accept_url, follow=True)
        self.assertContains(response, "currently Accepted")
        self.assertEqual(order.events.count(), 2)
        self.assertEqual(self.merchant_client.get(ready_url).status_code, 405)

    def test_checkout_rolls_back_when_the_initial_event_cannot_be_saved(self):
        with (
            patch.object(OrderStatusEvent.objects, "create", side_effect=RuntimeError("event failed")),
            self.assertRaisesRegex(RuntimeError, "event failed"),
        ):
            self.customer_client.post(self.checkout_url, self.checkout_payload())
        self.assertFalse(Order.objects.exists())


class ConcurrentCheckoutTests(TransactionTestCase):
    def test_concurrent_retries_create_one_order_with_one_event(self):
        merchant = Merchant.objects.create(name="Example Kitchen", slug="example-kitchen")
        product = create_product(merchant)
        customer = create_account("customer", AccountProfile.Role.CUSTOMER)
        start = Barrier(2)
        submission_key = uuid4()

        def submit():
            try:
                start.wait(timeout=5)
                return place_order(
                    customer=customer,
                    merchant=merchant,
                    delivery_address=ADDRESS,
                    submission_key=submission_key,
                    quantities={product.pk: 1},
                ).pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(submit)
            second = pool.submit(submit)
            self.assertEqual(first.result(timeout=15), second.result(timeout=15))

        order = Order.objects.get()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.events.count(), 1)

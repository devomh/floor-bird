from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountProfile
from accounts.roles import get_merchant_for_user, is_customer
from catalog.models import Merchant


class AccountRoleTests(TestCase):
    def test_roles_are_scoped_to_active_profile(self):
        user_model = get_user_model()
        customer = user_model.objects.create_user(username="customer")
        merchant_user = user_model.objects.create_user(username="merchant")
        merchant = Merchant.objects.create(name="Example Kitchen", slug="example-kitchen")
        AccountProfile.objects.create(user=customer, role=AccountProfile.Role.CUSTOMER)
        AccountProfile.objects.create(
            user=merchant_user, role=AccountProfile.Role.MERCHANT, merchant=merchant
        )

        self.assertTrue(is_customer(customer))
        self.assertIsNone(get_merchant_for_user(customer))
        self.assertFalse(is_customer(merchant_user))
        self.assertEqual(get_merchant_for_user(merchant_user), merchant)

        # Staff and anonymous users have no ordering privileges without a role.
        staff = user_model.objects.create_user(username="staff", is_staff=True)
        for actor in (staff, AnonymousUser()):
            self.assertFalse(is_customer(actor))
            self.assertIsNone(get_merchant_for_user(actor))

        customer.is_active = merchant_user.is_active = False
        self.assertFalse(is_customer(customer))
        self.assertIsNone(get_merchant_for_user(merchant_user))

    def test_database_rejects_merchant_profile_without_merchant(self):
        user = get_user_model().objects.create_user(username="merchant")

        with self.assertRaises(IntegrityError), transaction.atomic():
            AccountProfile.objects.create(user=user, role=AccountProfile.Role.MERCHANT)


class AccountSessionTests(TestCase):
    def test_login_keeps_the_next_page_and_logout_requires_post(self):
        password = "test-credentials"
        user = get_user_model().objects.create_user(username="customer", password=password)
        login_url = reverse("accounts:login")
        logout_url = reverse("accounts:logout")
        next_url = f"{reverse('catalog')}?source=login"

        login_page = self.client.get(login_url, {"next": next_url})
        self.assertContains(login_page, f'name="next" value="{next_url}"')
        response = self.client.post(
            login_url, {"username": user.username, "password": password, "next": next_url}
        )
        self.assertRedirects(response, next_url)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

        self.assertEqual(self.client.get(logout_url).status_code, 405)
        self.assertRedirects(self.client.post(logout_url), reverse("catalog"))
        self.assertNotIn("_auth_user_id", self.client.session)


class SeedDemoAccountsTests(TestCase):
    def setUp(self):
        call_command("seed_demo", stdout=StringIO())

    def test_creates_two_distinct_accounts_and_preserves_changed_passwords(self):
        first_output = StringIO()
        call_command("seed_demo_accounts", stdout=first_output)
        user_model = get_user_model()
        customer = user_model.objects.get(username="demo-customer")
        merchant_user = user_model.objects.get(username="demo-merchant")
        printed_credentials = dict(
            line.split(" password: ", 1) for line in first_output.getvalue().splitlines()
        )
        self.assertTrue(customer.check_password(printed_credentials[customer.username]))
        self.assertTrue(merchant_user.check_password(printed_credentials[merchant_user.username]))
        self.assertNotEqual(
            printed_credentials[customer.username], printed_credentials[merchant_user.username]
        )
        self.assertTrue(is_customer(customer))
        self.assertEqual(get_merchant_for_user(merchant_user).slug, "verde-kitchen")

        customer.set_password("customer-changed-password")
        customer.save(update_fields=["password"])
        updated_hash, merchant_hash = customer.password, merchant_user.password
        second_output = StringIO()
        call_command("seed_demo_accounts", stdout=second_output)

        self.assertEqual(user_model.objects.count(), 2)
        customer.refresh_from_db()
        merchant_user.refresh_from_db()
        self.assertEqual(customer.password, updated_hash)
        self.assertEqual(merchant_user.password, merchant_hash)
        self.assertNotIn(" password: ", second_output.getvalue())

    def test_username_collision_rolls_back_and_keeps_unrelated_user(self):
        user_model = get_user_model()
        existing = user_model.objects.create_user(username="demo-merchant")
        output = StringIO()

        with self.assertRaisesRegex(CommandError, "different profile"):
            call_command("seed_demo_accounts", stdout=output)

        self.assertEqual(list(user_model.objects.all()), [existing])
        self.assertFalse(AccountProfile.objects.exists())
        self.assertEqual(output.getvalue(), "")

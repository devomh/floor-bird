from django.conf import settings
from django.db import models


class AccountProfile(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        MERCHANT = "merchant", "Merchant"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_profile",
    )
    role = models.CharField(max_length=8, choices=Role)
    merchant = models.ForeignKey(
        "catalog.Merchant", on_delete=models.PROTECT, null=True, blank=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(role="customer", merchant__isnull=True)
                    | models.Q(role="merchant", merchant__isnull=False)
                ),
                name="accounts_role_merchant_check",
            )
        ]

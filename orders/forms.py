import re

from django import forms


QUANTITY_PREFIX = "quantity_"
PRODUCT_ID = re.compile(r"[1-9][0-9]{0,18}")
MAX_QUANTITY = 2**31 - 1


class CheckoutForm(forms.Form):
    submission_key = forms.UUIDField(widget=forms.HiddenInput)
    delivery_address = forms.CharField(
        label="Delivery address",
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, products, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visible_quantity_fields = {
            f"{QUANTITY_PREFIX}{product.pk}": product for product in products
        }
        field_names = set(self.visible_quantity_fields)
        if self.is_bound:
            # Include previously visible products so a retry can match the stored order.
            field_names.update(key for key in self.data if key.startswith(QUANTITY_PREFIX))
        for name in sorted(field_names):
            self.fields[name] = forms.IntegerField(
                label="Quantity",
                required=False,
                min_value=0,
                max_value=MAX_QUANTITY,
                initial=0,
            )

    @property
    def quantity_fields(self):
        return [(product, self[name]) for name, product in self.visible_quantity_fields.items()]

    def clean(self):
        cleaned = super().clean()
        quantities = {}
        for name in self.fields:
            if not name.startswith(QUANTITY_PREFIX):
                continue
            if name not in self.visible_quantity_fields and name in self.errors:
                raise forms.ValidationError("Check the quantities for the selected products.")
            quantity = cleaned.get(name)
            if quantity:
                product_id = name.removeprefix(QUANTITY_PREFIX)
                if not PRODUCT_ID.fullmatch(product_id) or int(product_id) > 2**63 - 1:
                    raise forms.ValidationError("Select products from this merchant's catalog.")
                quantities[int(product_id)] = quantity
        if not quantities and not self.errors:
            raise forms.ValidationError("Choose at least one product.")
        cleaned["quantities"] = quantities
        return cleaned

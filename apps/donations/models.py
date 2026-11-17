"""Timestamped support pledges; a pledge records an offer, not a payment."""
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Donation(models.Model):
    class Kind(models.TextChoices):
        GOODS = "goods", "Goods and supplies"
        TRANSPORT = "transport", "Transport"
        FUNDS = "funds", "Funds (INR)"

    class Status(models.TextChoices):
        PLEDGED = "pledged", "Offered"
        ASSIGNED = "assigned", "Assigned"
        DELIVERED = "delivered", "Delivered"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey("requests.ReliefRequest", on_delete=models.CASCADE, related_name="donations")
    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="donations")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    unit = models.CharField(max_length=40, help_text="For example: kits, trips, litres, or INR for funds.")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLEDGED)
    pledged_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-pledged_at", "-id"]

    def __str__(self):
        return f"{self.request.reference} · {self.quantity} {self.unit}"

"""Assignment, hand-over evidence, and the recipient's final confirmation."""
import uuid

from django.conf import settings
from django.db import models

from apps.requests.files import evidence_path, validate_evidence


class Delivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField("requests.ReliefRequest", on_delete=models.CASCADE, related_name="delivery")
    donation = models.OneToOneField("donations.Donation", on_delete=models.CASCADE, related_name="delivery")
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deliveries")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    recipient_name = models.CharField(max_length=120, blank=True)
    confirmation_note = models.TextField(max_length=2000, blank=True)
    proof = models.FileField(upload_to=evidence_path, validators=[validate_evidence], blank=True)
    proof_name = models.CharField(max_length=255, blank=True)
    recipient_confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="receipt_confirmations")
    recipient_confirmation = models.TextField(max_length=2000, blank=True)

    class Meta:
        ordering = ["-assigned_at", "-id"]

    def __str__(self):
        return f"{self.request.reference} · {self.responder.name}"

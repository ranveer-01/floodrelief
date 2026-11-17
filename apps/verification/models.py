"""Retained review decisions, including requests for additional information."""
import uuid

from django.conf import settings
from django.db import models

from apps.requests.files import evidence_path, validate_evidence


class Verification(models.Model):
    class Decision(models.TextChoices):
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        MORE_INFO = "more_info", "Needs more information"

    class Method(models.TextChoices):
        PHONE = "phone", "Phone confirmation"
        ON_SITE = "on_site", "On-site review"
        DOCUMENT = "document", "Supporting evidence"
        REQUESTER = "requester", "Requester supplied information"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey("requests.ReliefRequest", on_delete=models.CASCADE, related_name="verifications")
    decision = models.CharField(max_length=16, choices=Decision.choices)
    method = models.CharField(max_length=16, choices=Method.choices)
    notes = models.TextField(max_length=2000)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviews")
    reviewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    evidence = models.FileField(upload_to=evidence_path, validators=[validate_evidence], blank=True)
    evidence_name = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-reviewed_at", "-id"]

    def __str__(self):
        return f"{self.request.reference} · {self.get_decision_display()}"

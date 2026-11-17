"""Persistent, recipient-owned in-app updates."""
import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    request = models.ForeignKey("requests.ReliefRequest", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    event_key = models.CharField(max_length=160)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["recipient", "event_key"], name="unique_recipient_notification_event")]
        indexes = [models.Index(fields=["recipient", "read_at", "-created_at"])]

    def __str__(self):
        return self.title

"""Local notification delivery, scheduled only after a workflow commit succeeds."""
from django.conf import settings
from django.db import transaction
from django.db.models import Q

from apps.users.models import Role, User

from .models import Notification


def coordinator_ids():
    return User.objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(role__name__in=[Role.Name.NGO_STAFF, Role.Name.ADMIN])
    ).values_list("pk", flat=True)


def notify_after_commit(*, recipient_ids, event_key, title, body, request_id=None, actor_id=None):
    if not settings.ENABLE_IN_APP_NOTIFICATIONS:
        return
    recipients = set(recipient_ids) - {None, actor_id}

    def deliver():
        active_recipients = User.objects.filter(pk__in=recipients, is_active=True).values_list("pk", flat=True)
        for recipient_id in active_recipients:
            Notification.objects.get_or_create(
                recipient_id=recipient_id, event_key=event_key,
                defaults={"request_id": request_id, "title": title, "body": body},
            )

    # A failed supporting notification must not undo the committed relief action.
    transaction.on_commit(deliver, robust=True)

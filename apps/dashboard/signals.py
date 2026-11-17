from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.donations.models import Donation
from apps.requests.models import RequestStatus, StatusEvent
from apps.users.models import User
from apps.verification.models import Verification

from .notifications import coordinator_ids, notify_after_commit


@receiver(post_save, sender=StatusEvent)
def lifecycle_update(sender, instance, created, **kwargs):
    if not created:
        return
    relief_request = instance.request
    recipients = {relief_request.submitted_by_id}
    if instance.to_status == RequestStatus.RECEIVED:
        recipients.update(coordinator_ids())
    delivery = getattr(relief_request, "delivery", None)
    if delivery:
        recipients.add(delivery.responder_id)
    if instance.to_status in (RequestStatus.IN_PROGRESS, RequestStatus.DELIVERED, RequestStatus.CLOSED):
        recipients.update(coordinator_ids())
    notify_after_commit(
        recipient_ids=recipients, event_key=f"status:{instance.pk}", request_id=relief_request.pk,
        actor_id=instance.changed_by_id, title=f"{relief_request.reference}: {instance.get_to_status_display()}",
        body=f"The request moved to {instance.get_to_status_display()}. Open its timeline for the recorded details.",
    )


@receiver(post_save, sender=Verification)
def review_update(sender, instance, created, **kwargs):
    if not created or instance.decision == Verification.Decision.VERIFIED:
        return
    relief_request = instance.request
    recipients = coordinator_ids() if instance.decision == Verification.Decision.PENDING else [relief_request.submitted_by_id]
    notify_after_commit(
        recipient_ids=recipients, event_key=f"review:{instance.pk}", request_id=relief_request.pk,
        actor_id=instance.reviewed_by_id, title=f"{relief_request.reference}: {instance.get_decision_display()}",
        body="The review history has been updated. Open the request to read the decision or respond with additional information.",
    )


@receiver(post_save, sender=Donation)
def pledge_update(sender, instance, **kwargs):
    if instance.status not in (Donation.Status.PLEDGED, Donation.Status.WITHDRAWN):
        return
    relief_request = instance.request
    recipients = {relief_request.submitted_by_id, *coordinator_ids()}
    notify_after_commit(
        recipient_ids=recipients, event_key=f"pledge:{instance.pk}:{instance.status}", request_id=relief_request.pk,
        actor_id=instance.donor_id, title=f"{relief_request.reference}: support {instance.get_status_display().lower()}",
        body="A support offer changed. Open the request to review its current support pledges.",
    )


@receiver(pre_save, sender=User)
def remember_approval(sender, instance, **kwargs):
    instance._previous_support_approval = (
        sender.objects.filter(pk=instance.pk).values_list("support_approved", flat=True).first()
        if not instance._state.adding else None
    )


@receiver(post_save, sender=User)
def approval_update(sender, instance, created, **kwargs):
    previous = getattr(instance, "_previous_support_approval", None)
    if created or previous is None or previous == instance.support_approved:
        return
    approved = instance.can_support
    notify_after_commit(
        recipient_ids=[instance.pk], event_key=f"approval:{instance.pk}:{timezone.now().isoformat()}",
        title="Donor support approved" if approved else "Donor support approval updated",
        body="You can now browse verified requests and offer support." if approved else "Your account currently needs administrator approval to offer support.",
    )

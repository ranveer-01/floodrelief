from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.donations.models import Donation
from apps.requests.models import ReliefRequest, RequestStatus

from .models import Delivery


def _require_responder(by, delivery):
    if not (by.can_coordinate or (by.can_support and delivery.responder_id == by.pk)):
        raise PermissionDenied("Only the assigned responder and authorized staff can update delivery.")


@transaction.atomic
def assign_pledge(request_id, *, by, donation_id):
    if not by.can_coordinate:
        raise PermissionDenied("Only authorized staff can assign support.")
    relief_request = ReliefRequest.objects.select_for_update().get(pk=request_id)
    if relief_request.status != RequestStatus.VERIFIED:
        raise ValidationError("Only verified requests awaiting assignment can be assigned.")
    donation = Donation.objects.select_for_update().select_related("donor__role").filter(pk=donation_id, request=relief_request).first()
    if not donation or donation.status != Donation.Status.PLEDGED:
        raise ValidationError("Choose an available pledge for this request.")
    if not donation.donor.can_support:
        raise ValidationError("This donor no longer has approval to provide support.")
    if Delivery.objects.filter(request=relief_request).exists():
        raise ValidationError("This request already has an assigned delivery.")
    delivery = Delivery.objects.create(request=relief_request, donation=donation, responder=donation.donor, assigned_by=by)
    donation.status = Donation.Status.ASSIGNED
    donation.save(update_fields=["status", "updated_at"])
    relief_request.transition_to(RequestStatus.ASSIGNED, by=by, note="Support pledge assigned to a responder.")
    return delivery


@transaction.atomic
def start_delivery(request_id, *, by):
    relief_request = ReliefRequest.objects.select_for_update().get(pk=request_id)
    delivery = Delivery.objects.select_for_update().filter(request=relief_request).first()
    if not delivery:
        raise ValidationError("This request has no assigned delivery.")
    _require_responder(by, delivery)
    if relief_request.status != RequestStatus.ASSIGNED:
        raise ValidationError("Only an assigned delivery can be started.")
    delivery.started_at = timezone.now()
    delivery.save(update_fields=["started_at"])
    relief_request.transition_to(RequestStatus.IN_PROGRESS, by=by, note="Assigned responder started delivery.")
    return delivery


@transaction.atomic
def confirm_delivery(request_id, *, by, recipient_name, confirmation_note, proof=None):
    relief_request = ReliefRequest.objects.select_for_update().get(pk=request_id)
    delivery = Delivery.objects.select_for_update().filter(request=relief_request).first()
    if not delivery:
        raise ValidationError("This request has no assigned delivery.")
    _require_responder(by, delivery)
    if relief_request.status != RequestStatus.IN_PROGRESS:
        raise ValidationError("Start delivery before recording the hand-over.")
    if not 2 <= len(recipient_name.strip()) <= 120 or not 10 <= len(confirmation_note.strip()) <= 2000:
        raise ValidationError("Record the recipient's name and a complete hand-over confirmation.")
    delivery.recipient_name = recipient_name.strip()
    delivery.confirmation_note = confirmation_note.strip()
    delivery.delivered_at = timezone.now()
    if proof:
        delivery.proof = proof
        delivery.proof_name = proof.name
    delivery.full_clean()
    delivery.save()
    donation = Donation.objects.select_for_update().get(pk=delivery.donation_id)
    donation.status = Donation.Status.DELIVERED
    donation.save(update_fields=["status", "updated_at"])
    relief_request.transition_to(RequestStatus.DELIVERED, by=by, note="Support handed over; recipient confirmation recorded.")
    return delivery


@transaction.atomic
def confirm_receipt(request_id, *, by, confirmed, notes):
    relief_request = ReliefRequest.objects.select_for_update().get(pk=request_id)
    if not (by.can_coordinate or (by.is_active and relief_request.submitted_by_id == by.pk)):
        raise PermissionDenied("Only the requester and authorized staff can confirm receipt.")
    if relief_request.status != RequestStatus.DELIVERED:
        raise ValidationError("Receipt can only be confirmed after delivery.")
    delivery = Delivery.objects.select_for_update().filter(request=relief_request).first()
    if not delivery or not confirmed or not 10 <= len(notes.strip()) <= 2000:
        raise ValidationError("The recipient's confirmation is required before closing the request.")
    delivery.recipient_confirmed_at = timezone.now()
    delivery.confirmed_by = by
    delivery.recipient_confirmation = notes.strip()
    delivery.save(update_fields=["recipient_confirmed_at", "confirmed_by", "recipient_confirmation"])
    relief_request.transition_to(RequestStatus.CLOSED, by=by, note="Recipient confirmed receipt of support.")
    return delivery

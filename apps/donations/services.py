from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.requests.models import ReliefRequest, RequestStatus

from .models import Donation


@transaction.atomic
def pledge_support(request_id, *, by, kind, description, quantity, unit):
    if not by.can_support:
        raise PermissionDenied("Only approved donors and relief staff can offer support.")
    relief_request = ReliefRequest.objects.select_for_update().get(pk=request_id)
    if relief_request.status != RequestStatus.VERIFIED:
        raise ValidationError("Support can only be offered while a verified request is awaiting assignment.")
    if kind == Donation.Kind.FUNDS and unit.strip().upper() != "INR":
        raise ValidationError("Funds pledges must be recorded in INR.")
    donation = Donation(request=relief_request, donor=by, kind=kind,
                        description=description.strip(), quantity=quantity,
                        unit="INR" if kind == Donation.Kind.FUNDS else unit.strip())
    donation.full_clean()
    donation.save()
    relief_request.save(update_fields=["updated_at"])
    return donation


@transaction.atomic
def withdraw_pledge(donation_id, *, by):
    # Lock requests before pledges, matching the assignment service's lock order.
    request_id = Donation.objects.values_list("request_id", flat=True).get(pk=donation_id)
    relief_request = ReliefRequest.objects.select_for_update().get(pk=request_id)
    donation = Donation.objects.select_for_update().get(pk=donation_id)
    if not by.is_active or donation.donor_id != by.pk:
        raise PermissionDenied("Only the donor can withdraw this pledge.")
    if donation.status != Donation.Status.PLEDGED:
        raise ValidationError("An assigned or completed pledge cannot be withdrawn.")
    donation.status = Donation.Status.WITHDRAWN
    donation.save(update_fields=["status", "updated_at"])
    relief_request.save(update_fields=["updated_at"])
    return donation

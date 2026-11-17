from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.requests.models import ReliefRequest, RequestStatus

from .models import Verification


@transaction.atomic
def review_request(request_id, *, by, decision, method, notes, evidence=None, expected_revision=None):
    if not by.can_coordinate:
        raise PermissionDenied("Only authorized staff can verify relief requests.")
    relief_request = ReliefRequest.objects.select_for_update().get(pk=request_id)
    if relief_request.status != RequestStatus.RECEIVED:
        raise ValidationError("This request has already advanced beyond verification.")
    latest = relief_request.latest_verification
    if expected_revision is not None and expected_revision != (str(latest.pk) if latest else ""):
        raise ValidationError("Another review or response was recorded. Refresh this page before reviewing again.")
    if decision not in (Verification.Decision.VERIFIED, Verification.Decision.REJECTED, Verification.Decision.MORE_INFO):
        raise ValidationError("Choose a staff review decision.")
    if method not in (Verification.Method.PHONE, Verification.Method.ON_SITE, Verification.Method.DOCUMENT):
        raise ValidationError("Choose how this request was checked.")
    if not 10 <= len(notes.strip()) <= 2000:
        raise ValidationError("Add review notes between 10 and 2000 characters.")
    verification = Verification(
        request=relief_request, reviewed_by=by, decision=decision, method=method,
        notes=notes.strip(), evidence=evidence or "", evidence_name=evidence.name if evidence else "",
    )
    verification.full_clean()
    verification.save()
    relief_request.acknowledge(by=by, at=verification.reviewed_at)
    if decision == Verification.Decision.VERIFIED:
        relief_request.transition_to(RequestStatus.VERIFIED, by=by, note=notes.strip()[:240])
    return verification


@transaction.atomic
def respond_to_review(request_id, *, by, notes, evidence=None):
    relief_request = ReliefRequest.objects.select_for_update().get(pk=request_id)
    if not by.is_active or relief_request.submitted_by_id != by.pk:
        raise PermissionDenied("Only the requester can submit this response.")
    if relief_request.status != RequestStatus.RECEIVED or relief_request.verification_state != Verification.Decision.MORE_INFO:
        raise ValidationError("This request is not waiting for additional information.")
    if not 10 <= len(notes.strip()) <= 2000:
        raise ValidationError("Add information between 10 and 2000 characters.")
    verification = Verification(
        request=relief_request, reviewed_by=by, decision=Verification.Decision.PENDING,
        method=Verification.Method.REQUESTER, notes=notes.strip(),
        evidence=evidence or "", evidence_name=evidence.name if evidence else "",
    )
    verification.full_clean()
    verification.save()
    relief_request.save(update_fields=["updated_at"])
    return verification

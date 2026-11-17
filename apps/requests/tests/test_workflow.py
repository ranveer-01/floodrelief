from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.delivery.models import Delivery
from apps.delivery.services import assign_pledge, confirm_delivery, confirm_receipt, start_delivery
from apps.donations.models import Donation
from apps.donations.services import pledge_support, withdraw_pledge
from apps.requests.files import MAX_EVIDENCE_BYTES, validate_evidence
from apps.requests.models import ReliefRequest, RequestStatus, STATUS_ORDER
from apps.verification.services import respond_to_review, review_request

from .helpers import WorkflowTestCase


class LifecycleTests(WorkflowTestCase):
    def test_full_lifecycle_retains_six_events_and_recipient_confirmation(self):
        relief_request = self.make_request()
        delivery = self.deliver(relief_request)
        first_acknowledgement = relief_request.acknowledged_at
        self.assertEqual(relief_request.status, RequestStatus.DELIVERED)
        self.assertIsNone(delivery.recipient_confirmed_at)
        confirm_receipt(relief_request.pk, by=self.owner, confirmed=True,
                        notes="The named recipient confirms that all the supplies arrived.")
        relief_request.refresh_from_db()
        delivery.refresh_from_db()
        delivery.donation.refresh_from_db()
        self.assertEqual(relief_request.status, RequestStatus.CLOSED)
        self.assertEqual(list(relief_request.events.values_list("to_status", flat=True)), list(STATUS_ORDER))
        self.assertEqual(relief_request.acknowledged_at, first_acknowledgement)
        self.assertEqual(delivery.donation.status, Donation.Status.DELIVERED)
        self.assertEqual(delivery.confirmed_by, self.owner)
        self.assertIsNotNone(delivery.recipient_confirmed_at)
        self.assertGreaterEqual(relief_request.closed_at, delivery.recipient_confirmed_at)
        self.assertEqual(relief_request.verifications.count(), 1)
        self.assertEqual(relief_request.events.get(to_status="assigned").changed_by, self.staff)
        self.assertEqual(relief_request.events.get(to_status="delivered").changed_by, self.donor)

    def test_skipping_stages_or_editing_status_does_not_create_events(self):
        relief_request = self.make_request()
        with self.assertRaises(ValidationError):
            relief_request.transition_to(RequestStatus.DELIVERED, by=self.staff)
        relief_request.status = RequestStatus.VERIFIED
        with self.assertRaises(ValidationError):
            relief_request.save()
        relief_request.refresh_from_db()
        self.assertEqual(relief_request.status, RequestStatus.RECEIVED)
        self.assertEqual(relief_request.events.count(), 1)
        with self.assertRaises(ValidationError):
            self.make_request(status=RequestStatus.VERIFIED)

    def test_verification_requires_a_retained_staff_review(self):
        relief_request = self.make_request()
        with self.assertRaises(ValidationError):
            relief_request.transition_to(RequestStatus.VERIFIED, by=self.staff)
        self.assertEqual(relief_request.events.count(), 1)

    def test_nonstaff_cannot_review_or_assign(self):
        relief_request = self.make_request()
        for actor in (self.owner, self.donor, self.pending):
            with self.subTest(actor=actor.email), self.assertRaises(PermissionDenied):
                review_request(relief_request.pk, by=actor, decision="verified", method="phone", notes="Attempted unauthorized review.")
        self.verify(relief_request)
        pledge = pledge_support(relief_request.pk, by=self.donor, kind="goods", description="Supply enough water for everyone.", quantity=Decimal(24), unit="kits")
        with self.assertRaises(PermissionDenied):
            assign_pledge(relief_request.pk, by=self.donor, donation_id=pledge.pk)
        self.assertFalse(Delivery.objects.exists())

    def test_more_information_and_response_preserve_first_acknowledgement(self):
        relief_request = self.make_request()
        review = review_request(relief_request.pk, by=self.staff, decision="more_info", method="phone",
                                notes="Please confirm the camp location and number of families.", expected_revision="")
        relief_request.refresh_from_db()
        self.assertEqual(relief_request.acknowledged_at, review.reviewed_at)
        self.assertEqual(relief_request.status, RequestStatus.RECEIVED)
        self.assertEqual(relief_request.events.count(), 1)
        response = respond_to_review(relief_request.pk, by=self.owner,
                                     notes="The camp is at the school; six families need assistance.")
        relief_request.refresh_from_db()
        self.assertEqual(relief_request.verification_state, "pending")
        review_request(relief_request.pk, by=self.staff, decision="verified", method="phone",
                       notes="Confirmed the additional location and household information.", expected_revision=str(response.pk))
        relief_request.refresh_from_db()
        self.assertEqual(relief_request.acknowledged_at, review.reviewed_at)
        self.assertEqual(relief_request.verifications.count(), 3)
        self.assertEqual(relief_request.status, RequestStatus.VERIFIED)

    def test_rejection_acknowledges_without_donor_visibility(self):
        relief_request = self.make_request()
        review_request(relief_request.pk, by=self.staff, decision="rejected", method="phone", notes="The requester confirmed this need has already been met.")
        relief_request.refresh_from_db()
        self.assertEqual(relief_request.status, RequestStatus.RECEIVED)
        self.assertEqual(relief_request.verification_state, "rejected")
        self.assertIsNotNone(relief_request.acknowledged_at)
        with self.assertRaises(ValidationError):
            pledge_support(relief_request.pk, by=self.donor, kind="goods", description="An unauthorized offer for a rejected need.", quantity=Decimal(1), unit="kit")

    def test_stale_review_is_rejected_without_overwriting_history(self):
        relief_request = self.make_request()
        review_request(relief_request.pk, by=self.staff, decision="more_info", method="phone", notes="Please clarify the quantity of drinking water needed.", expected_revision="")
        with self.assertRaises(ValidationError):
            review_request(relief_request.pk, by=self.staff, decision="rejected", method="phone", notes="A decision submitted from an outdated review screen.", expected_revision="")
        self.assertEqual(relief_request.verifications.count(), 1)

    def test_only_owner_can_respond_to_an_information_request(self):
        relief_request = self.make_request()
        review_request(relief_request.pk, by=self.staff, decision="more_info", method="phone", notes="Please confirm the location before we send support.")
        with self.assertRaises(PermissionDenied):
            respond_to_review(relief_request.pk, by=self.other, notes="An unrelated person attempted to supply information.")
        self.assertEqual(relief_request.verifications.count(), 1)

    def test_approval_is_checked_when_pledging_and_again_when_assigning(self):
        relief_request = self.verify(self.make_request())
        with self.assertRaises(PermissionDenied):
            pledge_support(relief_request.pk, by=self.pending, kind="goods", description="Water supplies offered by a pending donor.", quantity=Decimal(1), unit="kit")
        pledge = pledge_support(relief_request.pk, by=self.donor, kind="goods", description="Water supplies offered by an approved donor.", quantity=Decimal(1), unit="kit")
        self.donor.support_approved = False
        self.donor.save(update_fields=["support_approved"])
        with self.assertRaises(ValidationError):
            assign_pledge(relief_request.pk, by=self.staff, donation_id=pledge.pk)
        pledge.refresh_from_db()
        self.assertEqual(pledge.status, Donation.Status.PLEDGED)
        self.assertFalse(Delivery.objects.exists())

    def test_funds_require_inr_and_positive_quantity(self):
        relief_request = self.verify(self.make_request())
        for quantity, unit in ((Decimal(0), "INR"), (Decimal(100), "USD")):
            with self.subTest(quantity=quantity, unit=unit), self.assertRaises(ValidationError):
                pledge_support(relief_request.pk, by=self.donor, kind="funds", description="Funds for the relief supplies.", quantity=quantity, unit=unit)
        pledge = pledge_support(relief_request.pk, by=self.donor, kind="funds", description="Funds for the relief supplies.", quantity=Decimal("2500"), unit="inr")
        self.assertEqual(pledge.unit, "INR")

    def test_withdrawal_requires_the_donor_and_an_unassigned_offer(self):
        relief_request = self.verify(self.make_request())
        pledge = pledge_support(relief_request.pk, by=self.donor, kind="goods", description="Water and supplies for the camp.", quantity=Decimal(24), unit="kits")
        with self.assertRaises(PermissionDenied):
            withdraw_pledge(pledge.pk, by=self.other_donor)
        withdraw_pledge(pledge.pk, by=self.donor)
        pledge.refresh_from_db()
        self.assertEqual(pledge.status, Donation.Status.WITHDRAWN)
        with self.assertRaises(ValidationError):
            assign_pledge(relief_request.pk, by=self.staff, donation_id=pledge.pk)
        assigned = self.assign(self.make_request()).donation
        with self.assertRaises(ValidationError):
            withdraw_pledge(assigned.pk, by=self.donor)

    def test_assignment_cannot_use_a_different_requests_pledge(self):
        first = self.verify(self.make_request())
        second = self.verify(self.make_request())
        pledge = pledge_support(second.pk, by=self.donor, kind="goods", description="Water for the other relief camp.", quantity=Decimal(24), unit="kits")
        with self.assertRaises(ValidationError):
            assign_pledge(first.pk, by=self.staff, donation_id=pledge.pk)
        self.assertFalse(Delivery.objects.exists())

    def test_other_donors_cannot_update_an_assigned_delivery(self):
        relief_request = self.make_request()
        self.assign(relief_request)
        with self.assertRaises(PermissionDenied):
            start_delivery(relief_request.pk, by=self.other_donor)
        start_delivery(relief_request.pk, by=self.donor)
        with self.assertRaises(PermissionDenied):
            confirm_delivery(relief_request.pk, by=self.other_donor, recipient_name="Recipient", confirmation_note="Another donor attempted to mark the delivery complete.")
        relief_request.refresh_from_db()
        self.assertEqual(relief_request.status, RequestStatus.IN_PROGRESS)

    def test_missing_hand_over_confirmation_leaves_delivery_in_progress(self):
        relief_request = self.make_request()
        delivery = self.assign(relief_request)
        start_delivery(relief_request.pk, by=self.donor)
        for name, note in (("", "Complete delivery note for the recipient."), ("Recipient", "short")):
            with self.subTest(name=name, note=note), self.assertRaises(ValidationError):
                confirm_delivery(relief_request.pk, by=self.donor, recipient_name=name, confirmation_note=note)
        delivery.refresh_from_db()
        relief_request.refresh_from_db()
        self.assertIsNone(delivery.delivered_at)
        self.assertEqual(relief_request.status, RequestStatus.IN_PROGRESS)
        self.assertEqual(relief_request.events.count(), 4)
        with self.assertRaises(ValidationError):
            relief_request.transition_to(RequestStatus.DELIVERED, by=self.donor)

    def test_receipt_requires_a_confirmed_recipient_and_an_authorized_actor(self):
        relief_request = self.make_request()
        delivery = self.deliver(relief_request)
        for actor, confirmed, expected in ((self.donor, True, PermissionDenied), (self.owner, False, ValidationError)):
            with self.subTest(actor=actor.email), self.assertRaises(expected):
                confirm_receipt(relief_request.pk, by=actor, confirmed=confirmed, notes="The supplies have reached the named recipient.")
        with self.assertRaises(ValidationError):
            relief_request.transition_to(RequestStatus.CLOSED, by=self.staff)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.recipient_confirmed_at)
        self.assertEqual(relief_request.events.count(), 5)

    def test_coordinator_can_record_phone_confirmation_for_anonymous_requests(self):
        relief_request = self.make_request(submitted_by=None)
        self.deliver(relief_request)
        confirm_receipt(relief_request.pk, by=self.staff, confirmed=True,
                        notes="The recipient confirmed receipt by phone with the coordinator.")
        relief_request.refresh_from_db()
        self.assertEqual(relief_request.status, RequestStatus.CLOSED)

    @override_settings(ACKNOWLEDGEMENT_TARGET_HOURS=2)
    def test_metric_uses_median_and_first_action_not_later_status_updates(self):
        now = timezone.now()
        for minutes in (15, 30, 60, 180):
            relief_request = self.make_request()
            ReliefRequest.objects.filter(pk=relief_request.pk).update(submitted_at=now - timedelta(hours=5), acknowledged_at=now - timedelta(hours=5) + timedelta(minutes=minutes))
        pending = self.make_request()
        ReliefRequest.objects.filter(pk=pending.pk).update(submitted_at=now - timedelta(hours=3))
        stats = ReliefRequest.objects.acknowledgement_stats()
        self.assertEqual(stats["median_minutes"], 45)
        self.assertEqual(stats["within_target_pct"], 75)
        self.assertEqual(stats["awaiting"], 1)
        self.assertEqual(stats["breaching"], 1)


class UploadValidationTests(WorkflowTestCase):
    def test_oversized_mislabeled_and_unsupported_files_are_rejected(self):
        files = [
            SimpleUploadedFile("proof.pdf", b"%PDF-" + b"x" * MAX_EVIDENCE_BYTES),
            SimpleUploadedFile("proof.png", b"not an actual PNG signature"),
            SimpleUploadedFile("proof.html", b"<html>unsafe attachment</html>"),
        ]
        for upload in files:
            with self.subTest(filename=upload.name), self.assertRaises(ValidationError):
                validate_evidence(upload)

    def test_invalid_proof_does_not_commit_delivery_or_change_the_pledge(self):
        relief_request = self.make_request()
        delivery = self.assign(relief_request)
        start_delivery(relief_request.pk, by=self.donor)
        with self.assertRaises(ValidationError):
            confirm_delivery(relief_request.pk, by=self.donor, recipient_name="Recipient", confirmation_note="The supplies were handed over to the recipient.", proof=SimpleUploadedFile("proof.png", b"mislabeled content"))
        delivery.refresh_from_db()
        delivery.donation.refresh_from_db()
        relief_request.refresh_from_db()
        self.assertIsNone(delivery.delivered_at)
        self.assertEqual(delivery.donation.status, Donation.Status.ASSIGNED)
        self.assertEqual(relief_request.status, RequestStatus.IN_PROGRESS)

    def test_supported_upload_keeps_its_stream_position(self):
        upload = SimpleUploadedFile("proof.PDF", b"%PDF-1.4\nTest proof document\n")
        validate_evidence(upload)
        self.assertEqual(upload.tell(), 0)

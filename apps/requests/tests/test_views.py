from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from apps.delivery.services import confirm_delivery, start_delivery
from apps.requests.models import ReliefRequest
from apps.verification.services import review_request

from .helpers import WorkflowTestCase


class RequestViewsTests(WorkflowTestCase):
    def test_anonymous_valid_submission_generates_reference_and_initial_event(self):
        response = self.client.post(reverse("requests:create"), {
            "contact_name": "Requester", "contact_phone": "+91 98765 43210", "category": "food_water",
            "urgency": "high", "people_affected": 6, "location": "Near the village school, Barpeta",
            "description": "Six households urgently need safe drinking water.", "status": "closed",
        })
        relief_request = ReliefRequest.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertRegex(relief_request.reference, r"^FRC-[A-Z2-9]{3}-[A-Z2-9]{3}$")
        self.assertEqual(relief_request.status, "received")
        self.assertIsNone(relief_request.submitted_by)
        self.assertEqual(relief_request.events.count(), 1)
        self.assertIn(str(relief_request.pk), response.url)

    def test_signed_in_submission_links_to_its_private_workspace(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("requests:create"), {
            "contact_name": "Requester", "contact_phone": "+91 98765 43210", "category": "shelter",
            "urgency": "high", "people_affected": 8, "location": "The school compound, Barpeta",
            "description": "Eight people need tents and dry bedding tonight.",
        })
        relief_request = ReliefRequest.objects.get()
        self.assertRedirects(response, reverse("requests:detail", args=[relief_request.pk]))
        self.assertEqual(relief_request.submitted_by, self.owner)

    def test_invalid_submission_creates_neither_request_nor_event(self):
        response = self.client.post(reverse("requests:create"), {"contact_name": "X", "contact_phone": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ReliefRequest.objects.exists())
        self.assertContains(response, "field__error")

    def test_coordinate_pair_and_ranges_are_validated(self):
        from apps.requests.forms import ReliefRequestForm

        data = {"contact_name": "Requester", "contact_phone": "+91 98765 43210", "category": "food_water", "urgency": "high", "people_affected": 6, "location": "Near the village school", "description": "Six households urgently need safe drinking water."}
        for coordinates in ({"latitude": "26.31"}, {"latitude": "91", "longitude": "181"}):
            with self.subTest(coordinates=coordinates):
                self.assertFalse(ReliefRequestForm({**data, **coordinates}).is_valid())
        self.assertTrue(ReliefRequestForm({**data, "latitude": "0", "longitude": "0"}).is_valid())

    def test_public_board_and_landing_omit_sensitive_request_text(self):
        relief_request = self.make_request()
        for url in (reverse("requests:list"), reverse("dashboard:landing")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, relief_request.reference)
                self.assertContains(response, "Barpeta")
                for private in (relief_request.contact_name, relief_request.contact_phone, relief_request.location, relief_request.description):
                    self.assertNotContains(response, private)

    def test_public_search_cannot_discover_contact_or_private_address(self):
        relief_request = self.make_request()
        for query in ("7931", "8827", "4751"):
            with self.subTest(query=query):
                response = self.client.get(reverse("requests:list"), {"q": query})
                self.assertNotContains(response, relief_request.reference)
        self.assertContains(self.client.get(reverse("requests:list"), {"q": "Barpeta"}), relief_request.reference)

    def test_account_dashboards_and_staff_queue_enforce_roles(self):
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 302)
        for actor in (self.owner, self.donor, self.pending):
            self.client.force_login(actor)
            self.assertEqual(self.client.get(reverse("verification:queue")).status_code, 403)
        self.client.force_login(self.pending)
        self.assertEqual(self.client.get(reverse("donations:available")).status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("verification:queue")).status_code, 200)

    def test_requester_cannot_open_another_requesters_record(self):
        relief_request = self.make_request()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("requests:detail", args=[relief_request.pk])).status_code, 404)

    def test_donors_browse_verified_requests_but_not_unverified_or_unrelated_deliveries(self):
        received = self.make_request()
        verified = self.verify(self.make_request())
        assigned = self.make_request()
        self.assign(assigned)
        self.client.force_login(self.other_donor)
        response = self.client.get(reverse("donations:available"))
        self.assertContains(response, verified.reference)
        self.assertNotContains(response, received.reference)
        self.assertNotContains(response, assigned.reference)
        self.assertEqual(self.client.get(reverse("requests:detail", args=[assigned.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("requests:detail", args=[received.pk])).status_code, 404)

    def test_unauthorized_actions_and_unknown_action_do_not_mutate_request(self):
        relief_request = self.verify(self.make_request())
        self.client.force_login(self.donor)
        url = reverse("requests:detail", args=[relief_request.pk])
        self.assertEqual(self.client.post(url, {"action": "review", "decision": "verified", "method": "phone", "notes": "Unauthorized review attempt."}).status_code, 403)
        self.assertEqual(self.client.post(url, {"action": "made_up_action"}).status_code, 400)
        self.assertEqual(relief_request.verifications.count(), 1)
        self.assertEqual(relief_request.events.count(), 2)

    def test_review_form_rejects_invalid_fields_without_server_error(self):
        relief_request = self.make_request()
        self.client.force_login(self.staff)
        response = self.client.post(reverse("requests:detail", args=[relief_request.pk]), {"action": "review", "decision": "verified", "method": "phone", "notes": "short"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at least 10 characters")
        self.assertFalse(relief_request.verifications.exists())

    def test_review_submission_records_action_and_redirects(self):
        relief_request = self.make_request()
        self.client.force_login(self.staff)
        url = reverse("requests:detail", args=[relief_request.pk])
        response = self.client.post(url, {"action": "review", "decision": "more_info", "method": "phone", "notes": "Please confirm the number of families needing supplies.", "revision": ""})
        self.assertRedirects(response, url)
        relief_request.refresh_from_db()
        self.assertIsNotNone(relief_request.acknowledged_at)
        self.assertEqual(relief_request.verification_state, "more_info")

    def test_csrf_is_required_for_workflow_mutations(self):
        relief_request = self.make_request()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        response = client.post(reverse("requests:detail", args=[relief_request.pk]), {"action": "review", "decision": "verified", "method": "phone", "notes": "A request without a CSRF token must not be accepted."})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(relief_request.verifications.exists())

    def test_duplicate_suggestions_are_staff_only_and_do_not_reject(self):
        first = self.make_request()
        second = self.make_request()
        url = reverse("requests:detail", args=[first.pk])
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(url), second.reference)
        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get(url), "Possibly related requests")
        first.refresh_from_db()
        self.assertEqual(first.status, "received")


class PrivateFileViewsTests(WorkflowTestCase):
    def setUp(self):
        self.temp_media = TemporaryDirectory()
        self.addCleanup(self.temp_media.cleanup)
        settings_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_request_and_review_evidence_are_private_attachments(self):
        relief_request = self.make_request(supporting_evidence=SimpleUploadedFile("request.pdf", b"%PDF-1.4\nRequest evidence"), evidence_name="request.pdf")
        review = review_request(relief_request.pk, by=self.staff, decision="more_info", method="document", notes="Please provide another detail about this supporting document.", evidence=SimpleUploadedFile("review.pdf", b"%PDF-1.4\nReview evidence"))
        urls = [reverse("requests:evidence", args=[relief_request.pk]), reverse("verification:evidence", args=[review.pk])]
        self.client.force_login(self.donor)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn("attachment;", response["Content-Disposition"])
            self.assertEqual(response["Content-Type"], "application/octet-stream")
            response.close()
        self.assertEqual(self.client.get("/media/" + relief_request.supporting_evidence.name).status_code, 404)

    def test_delivery_proof_is_shared_only_with_the_owner_responder_and_staff(self):
        relief_request = self.make_request()
        self.assign(relief_request)
        start_delivery(relief_request.pk, by=self.donor)
        delivery = confirm_delivery(relief_request.pk, by=self.donor, recipient_name="Recipient", confirmation_note="All supplies were handed over and confirmed on the ground.", proof=SimpleUploadedFile("proof.pdf", b"%PDF-1.4\nDelivery proof"))
        url = reverse("delivery:proof", args=[delivery.pk])
        self.client.force_login(self.other_donor)
        self.assertEqual(self.client.get(url).status_code, 404)
        for actor in (self.owner, self.donor, self.staff):
            self.client.force_login(actor)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response.close()

    def test_missing_attachment_returns_not_found(self):
        relief_request = self.make_request()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("requests:evidence", args=[relief_request.pk])).status_code, 404)

from decimal import Decimal
from unittest.mock import patch

from django.db import transaction
from django.test import override_settings
from django.urls import reverse

from apps.delivery.services import confirm_receipt
from apps.donations.services import pledge_support
from apps.requests.models import ReliefRequest
from apps.requests.tests.helpers import WorkflowTestCase
from apps.verification.services import review_request

from .models import Notification
from .notifications import notify_after_commit
from apps.users.models import Role, User


class NotificationTests(WorkflowTestCase):
    def test_review_update_is_delivered_only_after_commit_and_contains_no_private_notes(self):
        relief_request = self.make_request()
        with self.captureOnCommitCallbacks(execute=True):
            review_request(relief_request.pk, by=self.staff, decision="more_info", method="phone", notes="PRIVATE REVIEW NOTE 4367: please confirm the contact details.")
            self.assertFalse(Notification.objects.exists())
        notification = Notification.objects.get(recipient=self.owner)
        self.assertEqual(notification.request, relief_request)
        self.assertIn("Needs more information", notification.title)
        self.assertNotIn("PRIVATE REVIEW NOTE", notification.body)
        self.assertNotIn(relief_request.contact_phone, notification.body)

    def test_verified_review_produces_one_owner_notification(self):
        relief_request = self.make_request()
        with self.captureOnCommitCallbacks(execute=True):
            self.verify(relief_request)
        self.assertEqual(Notification.objects.filter(recipient=self.owner).count(), 1)
        self.assertIn("Verified", Notification.objects.get(recipient=self.owner).title)

    def test_rolled_back_relief_work_does_not_deliver_notifications(self):
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.make_request()
                raise RuntimeError("Rollback the core action")
        self.assertFalse(ReliefRequest.objects.exists())
        self.assertFalse(Notification.objects.exists())

    def test_notification_delivery_failure_does_not_undo_the_core_action(self):
        relief_request = self.make_request()
        with patch("apps.dashboard.notifications.Notification.objects.get_or_create", side_effect=RuntimeError("Notification store unavailable")):
            with self.assertLogs(level="ERROR"), self.captureOnCommitCallbacks(execute=True):
                self.verify(relief_request)
        relief_request.refresh_from_db()
        self.assertEqual(relief_request.status, "verified")
        self.assertEqual(relief_request.events.count(), 2)

    @override_settings(ENABLE_IN_APP_NOTIFICATIONS=False)
    def test_notifications_can_be_disabled_without_disabling_verification(self):
        relief_request = self.make_request()
        with self.captureOnCommitCallbacks(execute=True):
            self.verify(relief_request)
        self.assertEqual(relief_request.status, "verified")
        self.assertFalse(Notification.objects.exists())

    def test_repeated_event_is_deduplicated_for_each_recipient(self):
        with self.captureOnCommitCallbacks(execute=True):
            for _ in range(2):
                notify_after_commit(recipient_ids=[self.owner.pk, self.owner.pk, None], event_key="same-event", title="Test update", body="A repeated event is recorded once.")
        self.assertEqual(Notification.objects.count(), 1)

    def test_inbox_and_read_actions_are_scoped_to_the_signed_in_recipient(self):
        own = Notification.objects.create(recipient=self.owner, event_key="own", title="OWN UPDATE 1693", body="A private account update.")
        other = Notification.objects.create(recipient=self.other, event_key="other", title="OTHER UPDATE 2485", body="Another account's update.")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard:notifications"))
        self.assertContains(response, own.title)
        self.assertNotContains(response, other.title)
        own.refresh_from_db()
        self.assertIsNone(own.read_at)
        self.assertEqual(self.client.get(reverse("dashboard:read_notification", args=[own.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse("dashboard:read_notification", args=[other.pk])).status_code, 404)
        self.client.post(reverse("dashboard:read_all"))
        own.refresh_from_db()
        other.refresh_from_db()
        self.assertIsNotNone(own.read_at)
        self.assertIsNone(other.read_at)
        self.assertNotContains(self.client.get(reverse("dashboard:notifications"), {"unread": "1"}), own.title)

    def test_approval_change_notifies_the_donor(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.pending.support_approved = True
            self.pending.save(update_fields=["support_approved"])
        self.assertEqual(Notification.objects.get(recipient=self.pending).title, "Donor support approved")

    def test_assigned_responder_receives_the_assignment_update(self):
        relief_request = self.make_request()
        with self.captureOnCommitCallbacks(execute=True):
            self.assign(relief_request)
        self.assertTrue(Notification.objects.filter(recipient=self.donor, title__contains="Assigned").exists())


class ActivityTests(WorkflowTestCase):
    def test_personal_records_cannot_be_broadened_with_scope_parameter(self):
        own = self.make_request()
        other = self.make_request(submitted_by=self.other)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard:activity"), {"scope": "all"})
        self.assertContains(response, own.reference)
        self.assertNotContains(response, other.reference)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard:activity"), {"scope": "all"})
        self.assertContains(response, own.reference)
        self.assertContains(response, other.reference)

    def test_complete_activity_is_paginated_beyond_dashboard_preview(self):
        for _ in range(21):
            self.make_request()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard:activity"), {"page": 2})
        self.assertEqual(response.context["page_obj"].paginator.count, 21)
        self.assertEqual(len(response.context["page_obj"]), 1)
        self.assertContains(response, "Page 2 of 2")

    def test_pledge_activity_shows_only_the_donors_records(self):
        relief_request = self.verify(self.make_request())
        pledge_support(relief_request.pk, by=self.donor, kind="goods", description="OWN PLEDGE 2748 for the water supply.", quantity=Decimal(1), unit="kit")
        pledge_support(relief_request.pk, by=self.other_donor, kind="goods", description="OTHER PLEDGE 6942 for the water supply.", quantity=Decimal(1), unit="kit")
        self.client.force_login(self.donor)
        response = self.client.get(reverse("dashboard:activity"), {"kind": "pledges"})
        self.assertContains(response, "OWN PLEDGE 2748")
        self.assertNotContains(response, "OTHER PLEDGE 6942")

    def test_dashboard_measures_actual_recipient_confirmation_coverage(self):
        relief_request = self.make_request()
        self.deliver(relief_request)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.context["delivery_stats"]["coverage"], 0)
        confirm_receipt(relief_request.pk, by=self.owner, confirmed=True, notes="The recipient confirms that all promised supplies arrived.")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.context["delivery_stats"]["coverage"], 100)
        self.assertContains(response, "Requests by stage")

    def test_personal_dashboard_counts_only_the_owners_requests(self):
        self.make_request()
        awaiting_receipt = self.make_request()
        self.deliver(awaiting_receipt)
        closed = self.make_request()
        self.deliver(closed)
        confirm_receipt(closed.pk, by=self.owner, confirmed=True, notes="All promised supplies have reached the recipient.")
        self.deliver(self.make_request(submitted_by=self.other))
        self.client.force_login(self.owner)

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.context["my_request_stats"], {
            "total": 3, "active": 2, "awaiting_confirmation": 1,
        })


class RoleWorkspaceTests(WorkflowTestCase):
    def test_beneficiary_navigation_focuses_on_own_requests(self):
        own = self.make_request()
        other = self.verify(self.make_request(submitted_by=self.other))
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, own.reference)
        self.assertNotContains(response, other.reference)
        self.assertContains(response, "Beneficiary dashboard")
        self.assertNotContains(response, reverse("donations:available"))
        self.assertNotContains(response, reverse("verification:queue"))
        self.assertNotContains(response, reverse("users:manage_accounts"))

    def test_donor_discovery_uses_public_area_and_excludes_private_address(self):
        relief_request = self.verify(self.make_request())
        self.client.force_login(self.donor)
        for url in (reverse("dashboard:home"), reverse("donations:available")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, relief_request.reference)
                self.assertContains(response, relief_request.public_area)
                for private in (relief_request.location, relief_request.contact_phone, relief_request.description):
                    self.assertNotContains(response, private)
        response = self.client.get(reverse("donations:available"), {"q": "PRIVATE ADDRESS 8827"})
        self.assertNotContains(response, relief_request.reference)
        response = self.client.get(reverse("donations:available"), {"q": relief_request.public_area})
        self.assertContains(response, relief_request.reference)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("donations:available"), {"q": "PRIVATE ADDRESS 8827"}), relief_request.reference)

    def test_pending_donor_keeps_support_workspace_without_beneficiary_actions(self):
        self.verify(self.make_request())
        self.client.force_login(self.pending)
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Your donor account is awaiting approval")
        self.assertContains(response, "Your pledges")
        self.assertNotContains(response, "Request help")
        self.assertNotContains(response, reverse("donations:available"))
        self.assertEqual(response.context["available_count"], 0)

    def test_donor_default_activity_preserves_own_pledges_after_approval_revocation(self):
        relief_request = self.verify(self.make_request())
        pledge_support(relief_request.pk, by=self.donor, kind="goods", description="OWN ROLE WORKSPACE PLEDGE", quantity=Decimal(1), unit="kit")
        pledge_support(relief_request.pk, by=self.other_donor, kind="goods", description="OTHER ROLE WORKSPACE PLEDGE", quantity=Decimal(1), unit="kit")
        self.donor.support_approved = False
        self.donor.save(update_fields=["support_approved"])
        self.client.force_login(self.donor)
        response = self.client.get(reverse("dashboard:activity"), {"scope": "all"})
        self.assertEqual(response.context["kind"], "pledges")
        self.assertContains(response, "OWN ROLE WORKSPACE PLEDGE")
        self.assertNotContains(response, "OTHER ROLE WORKSPACE PLEDGE")
        self.assertFalse(response.context["all_records"])

    def test_coordinator_default_activity_is_global_and_mine_is_explicit(self):
        other = self.make_request()
        own = self.make_request(submitted_by=self.staff)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard:activity"))
        self.assertContains(response, other.reference)
        self.assertContains(response, own.reference)
        response = self.client.get(reverse("dashboard:activity"), {"scope": "mine"})
        self.assertContains(response, own.reference)
        self.assertNotContains(response, other.reference)

    def test_staff_and_administrator_have_distinct_priorities(self):
        relief_request = self.make_request()
        admin = User.objects.create_superuser("workspace-admin@example.test", "Account-password-29!", name="Administrator", role=Role.objects.get(name=Role.Name.ADMIN))
        self.client.force_login(self.staff)
        staff_response = self.client.get(reverse("dashboard:home"))
        self.assertContains(staff_response, relief_request.reference)
        self.assertContains(staff_response, "Review request")
        self.assertNotContains(staff_response, "Platform accounts")
        self.assertNotContains(staff_response, reverse("users:manage_accounts"))
        self.client.force_login(admin)
        admin_response = self.client.get(reverse("dashboard:home"))
        self.assertContains(admin_response, "Platform accounts")
        self.assertContains(admin_response, self.pending.email)
        self.assertContains(admin_response, reverse("users:manage_accounts"))
        self.assertNotContains(admin_response, "Your recent pledges")


class MapTests(WorkflowTestCase):
    @override_settings(GOOGLE_MAPS_API_KEY="")
    def test_map_uses_only_verified_active_requests_and_coarsened_positions(self):
        verified = self.verify(self.make_request(latitude=Decimal("26.317654"), longitude=Decimal("91.009876")))
        received = self.make_request()
        closed = self.make_request()
        self.deliver(closed)
        confirm_receipt(closed.pk, by=self.owner, confirmed=True, notes="The recipient confirmed that the support was delivered.")
        response = self.client.get(reverse("dashboard:map"))
        rows = response.context["map_requests"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reference"], verified.reference)
        self.assertEqual(rows[0]["latitude"], 26.32)
        self.assertEqual(rows[0]["longitude"], 91.01)
        for private in (verified.contact_phone, verified.contact_name, verified.location, verified.description, "26.317654", "91.009876", received.reference, closed.reference):
            self.assertNotContains(response, private)
        self.assertContains(response, "Interactive map is unavailable")
        self.assertNotContains(response, "maps-browser-key")

    @override_settings(GOOGLE_MAPS_API_KEY="browser-test-key")
    def test_maps_enhancement_is_optional_and_area_list_is_still_rendered(self):
        relief_request = self.verify(self.make_request(latitude=Decimal("26.31"), longitude=Decimal("91.0")))
        response = self.client.get(reverse("dashboard:map"))
        self.assertContains(response, "Load interactive map")
        self.assertContains(response, "map-request-data")
        self.assertContains(response, relief_request.reference)
        self.assertTrue(response.context["map_enabled"])

    def test_map_category_and_urgency_filters(self):
        food = self.verify(self.make_request())
        medical = self.verify(self.make_request(category="medical", urgency="critical"))
        response = self.client.get(reverse("dashboard:map"), {"category": "medical", "urgency": "critical"})
        self.assertContains(response, medical.reference)
        self.assertNotContains(response, food.reference)


class UpdateEndpointTests(WorkflowTestCase):
    def test_private_snapshot_contains_status_only_and_enforces_request_access(self):
        relief_request = self.make_request()
        url = reverse("requests:updates", args=[relief_request.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(set(response.json()), {"revision", "status", "label"})
        self.assertEqual(response.json()["status"], "received")
        self.assertIn("no-store", response["Cache-Control"])

    def test_review_and_pledge_changes_update_the_revision(self):
        relief_request = self.make_request()
        self.client.force_login(self.owner)
        url = reverse("requests:updates", args=[relief_request.pk])
        initial = self.client.get(url).json()["revision"]
        self.verify(relief_request)
        verified = self.client.get(url).json()["revision"]
        self.assertNotEqual(initial, verified)
        pledge_support(relief_request.pk, by=self.donor, kind="goods", description="Supplies to make the request record current.", quantity=Decimal(1), unit="kit")
        self.assertNotEqual(verified, self.client.get(url).json()["revision"])

    def test_public_update_signal_has_no_private_payload_and_requires_get(self):
        self.make_request()
        response = self.client.get(reverse("requests:board_updates"))
        self.assertEqual(set(response.json()), {"revision"})
        self.assertNotIn("PRIVATE", response.content.decode())
        self.assertEqual(self.client.post(reverse("requests:board_updates")).status_code, 405)

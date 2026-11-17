from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.delivery.models import Delivery
from apps.requests.models import ReliefRequest, StatusEvent
from apps.users.models import User


@override_settings(DEBUG=True)
class DemoTests(TestCase):
    def test_seed_is_repeatable_and_creates_consistent_records_for_all_roles(self):
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(ReliefRequest.objects.count(), 9)
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(Delivery.objects.count(), 5)
        self.assertEqual(Delivery.objects.filter(recipient_confirmed_at__isnull=False).count(), 2)
        timestamps = list(StatusEvent.objects.order_by("pk").values_list("pk", "changed_at"))
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(ReliefRequest.objects.count(), 9)
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(list(StatusEvent.objects.order_by("pk").values_list("pk", "changed_at")), timestamps)
        for relief_request in ReliefRequest.objects.exclude(status="received"):
            self.assertTrue(relief_request.verifications.exists())
        self.assertEqual(ReliefRequest.objects.acknowledgement_stats()["median_minutes"], 74)

    def test_fresh_rebuild_preserves_nondemo_requests(self):
        other = ReliefRequest.objects.create(contact_name="Other", contact_phone="9876543210", category="shelter", location="A different community", description="A request that is not part of the sample data.")
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", fresh=True, stdout=StringIO())
        self.assertTrue(ReliefRequest.objects.filter(pk=other.pk).exists())
        self.assertEqual(ReliefRequest.objects.count(), 10)

    @override_settings(DEBUG=False)
    def test_seed_refuses_to_create_demo_credentials_in_production(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertFalse(User.objects.exists())

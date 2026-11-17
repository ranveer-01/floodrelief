from decimal import Decimal

from django.test import TestCase

from apps.delivery.services import assign_pledge, confirm_delivery, start_delivery
from apps.donations.services import pledge_support
from apps.requests.models import ReliefRequest
from apps.users.models import Role, User
from apps.verification.services import review_request


class WorkflowTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        roles = {name: Role.objects.create(name=name) for name in Role.Name.values}
        cls.owner = User.objects.create_user("beneficiary@example.test", "Workflow-password-27!", name="Beneficiary", role=roles["victim"])
        cls.other = User.objects.create_user("other@example.test", "Workflow-password-27!", name="Other beneficiary", role=roles["victim"])
        cls.staff = User.objects.create_user("staff@example.test", "Workflow-password-27!", name="Coordinator", role=roles["ngo_staff"])
        cls.donor = User.objects.create_user("donor@example.test", "Workflow-password-27!", name="Approved donor", role=roles["donor"], support_approved=True)
        cls.pending = User.objects.create_user("pending@example.test", "Workflow-password-27!", name="Pending donor", role=roles["donor"])
        cls.other_donor = User.objects.create_user("second@example.test", "Workflow-password-27!", name="Second donor", role=roles["donor"], support_approved=True)

    def make_request(self, **overrides):
        fields = {
            "submitted_by": self.owner, "contact_name": "PRIVATE CONTACT 7931",
            "contact_phone": "+91 98765 43210", "category": "food_water", "urgency": "high",
            "location": "PRIVATE ADDRESS 8827, a specific household",
            "public_area": "Barpeta", "description": "PRIVATE SITUATION 4751: six families need drinking water.",
            "people_affected": 24,
        }
        fields.update(overrides)
        return ReliefRequest.objects.create(**fields)

    def verify(self, relief_request):
        review_request(relief_request.pk, by=self.staff, decision="verified", method="phone",
                       notes="Confirmed the need with the requester by phone.")
        relief_request.refresh_from_db()
        return relief_request

    def assign(self, relief_request):
        self.verify(relief_request)
        pledge = pledge_support(relief_request.pk, by=self.donor, kind="goods",
                                description="Drinking water and ration kits for six families.",
                                quantity=Decimal("24"), unit="kits")
        delivery = assign_pledge(relief_request.pk, by=self.staff, donation_id=pledge.pk)
        relief_request.refresh_from_db()
        return delivery

    def deliver(self, relief_request):
        self.assign(relief_request)
        start_delivery(relief_request.pk, by=self.donor)
        delivery = confirm_delivery(relief_request.pk, by=self.donor, recipient_name="Recipient",
                                    confirmation_note="All twenty-four kits were handed over to the recipient.")
        relief_request.refresh_from_db()
        return delivery

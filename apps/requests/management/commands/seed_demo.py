"""
Populate the four roles and a realistic board of relief requests.

    python manage.py seed_demo          # add demo rows
    python manage.py seed_demo --fresh  # rebuild only matching demo requests

Timestamps are backdated so the landing page shows a real median
time-to-acknowledgement instead of an empty state during the demo.
"""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.delivery.models import Delivery
from apps.delivery.services import assign_pledge, confirm_delivery, confirm_receipt, start_delivery
from apps.donations.models import Donation
from apps.donations.services import pledge_support
from apps.verification.models import Verification
from apps.verification.services import review_request

from apps.requests.models import (
    Category,
    ReliefRequest,
    RequestStatus,
    StatusEvent,
    Urgency,
)
from apps.users.models import Role, User

ROLE_DESCRIPTIONS = {
    Role.Name.VICTIM: "Files and tracks relief requests.",
    Role.Name.DONOR: "Pledges goods, transport or funds.",
    Role.Name.NGO_STAFF: "Verifies, assigns and delivers.",
    Role.Name.ADMIN: "Oversees the whole operation.",
}

# (category, urgency, people, location, description, age_minutes, [(status, minutes_after)])
SAMPLES = [
    (
        Category.RESCUE, Urgency.CRITICAL, 23,
        "Ward 4 rooftop, near the old jute mill, Barpeta",
        "Six families stranded on a school roof since last night. Two elderly, "
        "one infant. Water still rising against the north wall.",
        38, [],
    ),
    (
        Category.FOOD_WATER, Urgency.HIGH, 140,
        "Relief camp 2, Govt. Higher Secondary School, Dhubri",
        "Camp has 140 people and dry rations for one more day. Drinking water "
        "cans and baby food needed by tomorrow morning.",
        95, [(RequestStatus.VERIFIED, 41), (RequestStatus.ASSIGNED, 66)],
    ),
    (
        Category.MEDICAL, Urgency.CRITICAL, 4,
        "Char area, 3 km east of Rowmari ferry ghat",
        "Diabetic patient out of insulin for two days, no cold storage. Also a "
        "pregnant woman due this week with no way to reach the health centre.",
        210, [(RequestStatus.VERIFIED, 22), (RequestStatus.ASSIGNED, 48),
              (RequestStatus.IN_PROGRESS, 96)],
    ),
    (
        Category.SHELTER, Urgency.HIGH, 52,
        "Embankment road, Kharupetia block",
        "Eleven families living under tarpaulin on the embankment since the "
        "breach. Need tents and ground sheets before the next spell of rain.",
        400, [(RequestStatus.VERIFIED, 74), (RequestStatus.ASSIGNED, 130),
              (RequestStatus.IN_PROGRESS, 180), (RequestStatus.DELIVERED, 305)],
    ),
    (
        Category.SANITATION, Urgency.MEDIUM, 300,
        "Relief camp 5, community hall, Nalbari",
        "Two toilets for roughly 300 people. Requesting bleaching powder, "
        "disinfectant and portable sanitation units.",
        520, [(RequestStatus.VERIFIED, 150)],
    ),
    (
        Category.CLOTHING, Urgency.MEDIUM, 68,
        "Bhogdoi riverside colony, Jorhat",
        "Households returned to silted homes with nothing dry. Need blankets, "
        "adult and children's clothing, and bedding.",
        1500, [(RequestStatus.VERIFIED, 88), (RequestStatus.ASSIGNED, 160),
               (RequestStatus.IN_PROGRESS, 240), (RequestStatus.DELIVERED, 420),
               (RequestStatus.CLOSED, 900)],
    ),
    (
        Category.FOOD_WATER, Urgency.HIGH, 85,
        "Majuli island, Kamalabari ghat cluster",
        "Ferry service suspended, shops closed. Rice, pulses, oil and water "
        "purification tablets needed for 20 households.",
        160, [(RequestStatus.VERIFIED, 52)],
    ),
    (
        Category.OTHER, Urgency.LOW, 12,
        "Sonitpur, village school compound",
        "School compound flooded with stagnant water. Requesting a pump so "
        "classes can restart next week.",
        2600, [(RequestStatus.VERIFIED, 190), (RequestStatus.ASSIGNED, 400),
               (RequestStatus.IN_PROGRESS, 700), (RequestStatus.DELIVERED, 1100),
               (RequestStatus.CLOSED, 2100)],
    ),
    (
        Category.MEDICAL, Urgency.HIGH, 9,
        "Ward 7 health sub-centre, Lakhimpur",
        "Sub-centre out of ORS, antiseptic and snakebite antivenom. Three "
        "suspected leptospirosis cases waiting.",
        26, [],
    ),
]

CONTACTS = [
    ("Anjali Barman", "+91 98640 11223"),
    ("Rafiqul Islam", "+91 97070 55418"),
    ("Priya Deka", "+91 90850 33127"),
    ("Sanjib Gogoi", "+91 88110 47762"),
    ("Mitali Das", "+91 99570 29084"),
    ("Hemanta Saikia", "+91 70020 66431"),
    ("Nazrul Haque", "+91 91010 78256"),
    ("Bipul Nath", "+91 87220 91345"),
    ("Runjun Phukan", "+91 94350 60918"),
]

# Approximate district/town centres, for the optional demonstration map.
MAP_AREAS = [
    ("Barpeta", "26.320000", "91.000000"),
    ("Dhubri", "26.020000", "89.970000"),
    ("Rowmari", "25.570000", "89.840000"),
    ("Kharupetia", "26.510000", "92.040000"),
    ("Nalbari", "26.450000", "91.440000"),
    ("Jorhat", "26.750000", "94.220000"),
    ("Majuli", "26.950000", "94.200000"),
    ("Sonitpur", "26.650000", "92.800000"),
    ("Lakhimpur", "27.230000", "94.100000"),
]


class Command(BaseCommand):
    help = "Seed roles and a realistic set of relief requests for the demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Rebuild matching demo requests only; retain other requests and all accounts.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo accounts and data can only be created with DEBUG=True.")
        for name, description in ROLE_DESCRIPTIONS.items():
            role, created = Role.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            if created:
                self.stdout.write(f"  role created: {role}")

        victim = self.demo_user("victim", Role.Name.VICTIM, "Demo beneficiary")
        donor = self.demo_user("donor", Role.Name.DONOR, "Demo relief provider", support_approved=True)
        staff = self.demo_user("staff", Role.Name.NGO_STAFF, "Manshaan Singh", is_staff=True)
        self.demo_user("admin", Role.Name.ADMIN, "Demo administrator", is_staff=True, is_superuser=True)

        if options["fresh"]:
            deleted = 0
            for sample in SAMPLES:
                rows, _ = ReliefRequest.objects.filter(location=sample[3], description=sample[4]).delete()
                deleted += rows
            self.stdout.write(f"  cleared {deleted} matching demo row(s)")

        now = timezone.now()
        created_count = 0

        for index, (category, urgency, people, location, description, age, hops) in enumerate(
            SAMPLES
        ):
            contact_name, contact_phone = CONTACTS[index % len(CONTACTS)]
            existing = ReliefRequest.objects.filter(location=location, description=description).first()
            if existing:
                self.complete_historical_demo(existing, staff, donor, victim, MAP_AREAS[index])
                continue

            area, latitude, longitude = MAP_AREAS[index]

            relief_request = ReliefRequest.objects.create(
                category=category,
                urgency=urgency,
                people_affected=people,
                location=location,
                description=description,
                contact_name=contact_name,
                contact_phone=contact_phone,
                submitted_by=victim,
                public_area=area,
                latitude=Decimal(latitude),
                longitude=Decimal(longitude),
            )
            submitted_at = now - timedelta(minutes=age)

            # auto_now_add fields can only be rewritten with an UPDATE.
            ReliefRequest.objects.filter(pk=relief_request.pk).update(submitted_at=submitted_at)
            StatusEvent.objects.filter(request=relief_request).update(changed_at=submitted_at)
            relief_request.refresh_from_db()

            for status, offset in hops:
                if status == RequestStatus.VERIFIED:
                    review_request(relief_request.pk, by=staff, decision="verified", method="phone",
                                   notes="Demonstration request checked with the beneficiary by phone.")
                elif status == RequestStatus.ASSIGNED:
                    pledge = pledge_support(relief_request.pk, by=donor, kind="goods",
                                            description="Demonstration relief supplies for this request.",
                                            quantity=Decimal(people), unit="kits")
                    assign_pledge(relief_request.pk, by=staff, donation_id=pledge.pk)
                elif status == RequestStatus.IN_PROGRESS:
                    start_delivery(relief_request.pk, by=donor)
                elif status == RequestStatus.DELIVERED:
                    confirm_delivery(relief_request.pk, by=donor, recipient_name=contact_name,
                                     confirmation_note="Demonstration supplies handed over to the named recipient.")
                elif status == RequestStatus.CLOSED:
                    confirm_receipt(relief_request.pk, by=victim, confirmed=True,
                                    notes="Demonstration recipient confirms that the supplies arrived.")
                relief_request.refresh_from_db()
                event = relief_request.events.get(to_status=status)
                StatusEvent.objects.filter(pk=event.pk).update(
                    changed_at=submitted_at + timedelta(minutes=offset)
                )

            if hops:
                updates = {"acknowledged_at": submitted_at + timedelta(minutes=hops[0][1])}
                if hops[-1][0] == RequestStatus.CLOSED:
                    updates["closed_at"] = submitted_at + timedelta(minutes=hops[-1][1])
                ReliefRequest.objects.filter(pk=relief_request.pk).update(**updates)

            self.backdate_records(relief_request, submitted_at, dict(hops))

            created_count += 1

        stats = ReliefRequest.objects.acknowledgement_stats()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_count} request(s). "
                f"Board now holds {stats['total']}, "
                f"{stats['awaiting']} awaiting acknowledgement."
            )
        )

    def demo_user(self, account, role_name, name, **flags):
        user, created = User.objects.get_or_create(
            email=f"{account}@floodrelief.test",
            defaults={"name": name, "phone": "+91 90000 00001", "role": Role.objects.get(name=role_name), **flags},
        )
        if created:
            user.set_password("floodrelief")
            user.save(update_fields=["password"])
            self.stdout.write(f"  demo account: {user.email} / floodrelief")
        return user

    def backdate_records(self, relief_request, submitted_at, hops):
        times = {status: submitted_at + timedelta(minutes=offset) for status, offset in hops.items()}
        if RequestStatus.VERIFIED in times:
            Verification.objects.filter(request=relief_request).update(reviewed_at=times[RequestStatus.VERIFIED])
        if RequestStatus.ASSIGNED in times:
            Donation.objects.filter(request=relief_request).update(
                pledged_at=times[RequestStatus.VERIFIED], updated_at=times.get(RequestStatus.DELIVERED, times[RequestStatus.ASSIGNED]),
            )
            Delivery.objects.filter(request=relief_request).update(
                assigned_at=times[RequestStatus.ASSIGNED], started_at=times.get(RequestStatus.IN_PROGRESS),
                delivered_at=times.get(RequestStatus.DELIVERED), recipient_confirmed_at=times.get(RequestStatus.CLOSED),
            )
        if times:
            ReliefRequest.objects.filter(pk=relief_request.pk).update(updated_at=max(times.values()))

    def complete_historical_demo(self, relief_request, staff, donor, victim, area):
        """Enrich old sample rows; preserve their status trail and original timestamps."""
        fields = []
        if relief_request.submitted_by_id is None:
            relief_request.submitted_by = victim
            fields.append("submitted_by")
        if not relief_request.public_area:
            relief_request.public_area, latitude, longitude = area
            relief_request.latitude, relief_request.longitude = Decimal(latitude), Decimal(longitude)
            fields += ["public_area", "latitude", "longitude"]
        if fields:
            relief_request.save(update_fields=fields)
        times = {event.to_status: event.changed_at for event in relief_request.events.all()}
        if relief_request.status_index >= 1 and not relief_request.verifications.exists():
            review = Verification.objects.create(
                request=relief_request, reviewed_by=staff, decision="verified", method="phone",
                notes="Historical demonstration review reconstructed from the retained status trail.",
            )
            Verification.objects.filter(pk=review.pk).update(
                reviewed_at=times.get(RequestStatus.VERIFIED, relief_request.acknowledged_at or relief_request.submitted_at),
            )
        if relief_request.status_index >= 2 and not Delivery.objects.filter(request=relief_request).exists():
            delivered = relief_request.status_index >= 4
            closed = relief_request.is_closed
            pledge = Donation.objects.create(
                request=relief_request, donor=donor, kind="goods", quantity=Decimal(relief_request.people_affected),
                unit="kits", description="Historical demonstration support reconstructed from the status trail.",
                status=Donation.Status.DELIVERED if delivered else Donation.Status.ASSIGNED,
            )
            Donation.objects.filter(pk=pledge.pk).update(pledged_at=times.get(RequestStatus.VERIFIED, relief_request.submitted_at))
            delivery = Delivery.objects.create(
                request=relief_request, donation=pledge, responder=donor, assigned_by=staff,
                started_at=times.get(RequestStatus.IN_PROGRESS), delivered_at=times.get(RequestStatus.DELIVERED),
                recipient_name=relief_request.contact_name if delivered else "",
                confirmation_note="Historical demonstration hand-over reconstructed from the status trail." if delivered else "",
                recipient_confirmed_at=times.get(RequestStatus.CLOSED), confirmed_by=victim if closed else None,
                recipient_confirmation="Historical demonstration receipt reconstructed from the status trail." if closed else "",
            )
            Delivery.objects.filter(pk=delivery.pk).update(assigned_at=times.get(RequestStatus.ASSIGNED, relief_request.submitted_at))

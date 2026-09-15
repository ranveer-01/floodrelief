"""
Populate the four roles and a realistic board of relief requests.

    python manage.py seed_demo          # add demo rows
    python manage.py seed_demo --fresh  # wipe requests first

Timestamps are backdated so the landing page shows a real median
time-to-acknowledgement instead of an empty state during the demo.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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


class Command(BaseCommand):
    help = "Seed roles and a realistic set of relief requests for the demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing relief requests before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        for name, description in ROLE_DESCRIPTIONS.items():
            role, created = Role.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            if created:
                self.stdout.write(f"  role created: {role}")

        staff_role = Role.objects.get(name=Role.Name.NGO_STAFF)
        staff, created = User.objects.get_or_create(
            email="staff@floodrelief.test",
            defaults={"name": "Manshaan Singh", "role": staff_role, "is_staff": True},
        )
        if created:
            staff.set_password("floodrelief")
            staff.save(update_fields=["password"])
            self.stdout.write("  demo NGO user: staff@floodrelief.test / floodrelief")

        if options["fresh"]:
            deleted, _ = ReliefRequest.objects.all().delete()
            self.stdout.write(f"  cleared {deleted} existing row(s)")

        now = timezone.now()
        created_count = 0

        for index, (category, urgency, people, location, description, age, hops) in enumerate(
            SAMPLES
        ):
            contact_name, contact_phone = CONTACTS[index % len(CONTACTS)]
            if ReliefRequest.objects.filter(location=location, description=description).exists():
                continue

            relief_request = ReliefRequest.objects.create(
                category=category,
                urgency=urgency,
                people_affected=people,
                location=location,
                description=description,
                contact_name=contact_name,
                contact_phone=contact_phone,
            )
            submitted_at = now - timedelta(minutes=age)

            # auto_now_add fields can only be rewritten with an UPDATE.
            ReliefRequest.objects.filter(pk=relief_request.pk).update(submitted_at=submitted_at)
            StatusEvent.objects.filter(request=relief_request).update(changed_at=submitted_at)
            relief_request.refresh_from_db()

            for status, offset in hops:
                event = relief_request.transition_to(
                    status, by=staff, note="Seeded demo data."
                )
                StatusEvent.objects.filter(pk=event.pk).update(
                    changed_at=submitted_at + timedelta(minutes=offset)
                )

            if hops:
                updates = {"acknowledged_at": submitted_at + timedelta(minutes=hops[0][1])}
                if hops[-1][0] == RequestStatus.CLOSED:
                    updates["closed_at"] = submitted_at + timedelta(minutes=hops[-1][1])
                ReliefRequest.objects.filter(pk=relief_request.pk).update(**updates)

            created_count += 1

        stats = ReliefRequest.objects.acknowledgement_stats()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_count} request(s). "
                f"Board now holds {stats['total']}, "
                f"{stats['awaiting']} awaiting acknowledgement."
            )
        )

"""
The traceable relief-request lifecycle.

    Received -> Verified -> Assigned -> In Progress -> Delivered -> Closed

Every transition is written to `StatusEvent` with a timestamp, which is what
makes the proposal's primary metric — time-to-acknowledgement — measurable
rather than anecdotal.
"""
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

from .files import evidence_path, validate_evidence

# Unambiguous alphabet for the human-readable reference code (no 0/O/1/I).
REFERENCE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


class RequestStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    VERIFIED = "verified", "Verified"
    ASSIGNED = "assigned", "Assigned"
    IN_PROGRESS = "in_progress", "In progress"
    DELIVERED = "delivered", "Delivered"
    CLOSED = "closed", "Closed"


#: Canonical order of the lifecycle. Used for the progress tracker in the UI.
STATUS_ORDER = [
    RequestStatus.RECEIVED,
    RequestStatus.VERIFIED,
    RequestStatus.ASSIGNED,
    RequestStatus.IN_PROGRESS,
    RequestStatus.DELIVERED,
    RequestStatus.CLOSED,
]

#: Short verbs shown under each node of the tracker.
STATUS_CAPTIONS = {
    RequestStatus.RECEIVED: "Logged with a reference number",
    RequestStatus.VERIFIED: "Checked by NGO staff",
    RequestStatus.ASSIGNED: "Matched to a responder",
    RequestStatus.IN_PROGRESS: "Supplies on the move",
    RequestStatus.DELIVERED: "Handed over on the ground",
    RequestStatus.CLOSED: "Confirmed by the requester",
}


class Category(models.TextChoices):
    RESCUE = "rescue", "Rescue / evacuation"
    MEDICAL = "medical", "Medical aid"
    FOOD_WATER = "food_water", "Food & drinking water"
    SHELTER = "shelter", "Shelter"
    CLOTHING = "clothing", "Clothing & bedding"
    SANITATION = "sanitation", "Sanitation & hygiene"
    OTHER = "other", "Other"


class Urgency(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


#: Sort weight so critical requests surface first regardless of insert order.
URGENCY_WEIGHT = {
    Urgency.CRITICAL: 0,
    Urgency.HIGH: 1,
    Urgency.MEDIUM: 2,
    Urgency.LOW: 3,
}


class ReliefRequestQuerySet(models.QuerySet):
    def open(self):
        return self.exclude(status=RequestStatus.CLOSED)

    def awaiting_acknowledgement(self):
        return self.filter(acknowledged_at__isnull=True)

    def prioritized(self):
        return self.annotate(
            urgency_rank=models.Case(
                *[
                    models.When(urgency=value, then=models.Value(weight))
                    for value, weight in URGENCY_WEIGHT.items()
                ],
                default=models.Value(9),
                output_field=models.IntegerField(),
            )
        ).order_by("urgency_rank", "submitted_at")

    def acknowledged(self):
        return self.filter(acknowledged_at__isnull=False)

    def breaching_target(self):
        """Still sitting at 'Received' past the acknowledgement target."""
        cutoff = timezone.now() - timedelta(hours=settings.ACKNOWLEDGEMENT_TARGET_HOURS)
        return self.awaiting_acknowledgement().filter(submitted_at__lt=cutoff)

    def acknowledgement_stats(self):
        """
        Aggregate the proposal's primary metric.

        Returns median minutes to acknowledgement and the share answered inside
        the target window. Median (not mean) so one stale request doesn't skew
        the headline number.
        """
        durations = [
            r.acknowledgement_minutes
            for r in self.acknowledged().only("submitted_at", "acknowledged_at")
        ]
        durations = sorted(d for d in durations if d is not None)
        target_minutes = settings.ACKNOWLEDGEMENT_TARGET_HOURS * 60

        median = None
        if durations:
            mid = len(durations) // 2
            if len(durations) % 2:
                median = durations[mid]
            else:
                median = (durations[mid - 1] + durations[mid]) / 2

        within = sum(1 for d in durations if d <= target_minutes)
        return {
            "total": self.count(),
            "acknowledged": len(durations),
            "awaiting": self.awaiting_acknowledgement().count(),
            "breaching": self.breaching_target().count(),
            "median_minutes": median,
            "within_target": within,
            "within_target_pct": round(within / len(durations) * 100) if durations else None,
            "target_hours": settings.ACKNOWLEDGEMENT_TARGET_HOURS,
        }


class ReliefRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
        help_text="Short code the requester can quote on a phone call.",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relief_requests",
        help_text="Set when a signed-in user submits. Blank for walk-in / phone entries.",
    )
    # Contact details keep an anonymous submission reachable — without them a
    # request logged from a public phone is untraceable, which defeats the point.
    contact_name = models.CharField(max_length=120)
    contact_phone = models.CharField(max_length=20)

    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(help_text="What is needed, for how many people.")
    location = models.CharField(max_length=200, help_text="Village / ward, landmark, district.")
    public_area = models.CharField(
        max_length=120, blank=True,
        help_text="Optional district or town shown publicly. Keep addresses and contact details in the private location.",
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    supporting_evidence = models.FileField(
        upload_to=evidence_path, validators=[validate_evidence], blank=True,
    )
    evidence_name = models.CharField(max_length=255, blank=True)
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.MEDIUM)
    people_affected = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.RECEIVED,
        db_index=True,
    )

    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="When the request first moved past 'Received'.",
    )
    closed_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = ReliefRequestQuerySet.as_manager()

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "relief request"
        indexes = [
            models.Index(fields=["status", "-submitted_at"]),
            models.Index(fields=["urgency"]),
        ]

    def __str__(self):
        return f"{self.reference} · {self.get_category_display()} · {self.location}"

    def get_absolute_url(self):
        return f"{reverse('requests:list')}?highlight={self.pk}#req-{self.pk}"

    def clean(self):
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError("Provide both latitude and longitude, or leave both empty.")

    # --- Persistence --------------------------------------------------------
    @classmethod
    def generate_reference(cls):
        while True:
            body = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
            reference = f"FRC-{body[:3]}-{body[3:]}"
            if not cls.objects.filter(reference=reference).exists():
                return reference

    def save(self, *args, **kwargs):
        creating = self._state.adding
        if creating and self.status != RequestStatus.RECEIVED:
            raise ValidationError("New requests must enter at Received.")
        if not creating and (
            kwargs.get("update_fields") is None or "status" in kwargs["update_fields"]
        ):
            previous = type(self).objects.values_list("status", flat=True).get(pk=self.pk)
            if previous != self.status:
                raise ValidationError("Use the workflow actions to change a request's status.")
        with transaction.atomic():
            if not self.reference:
                self.reference = self.generate_reference()
            super().save(*args, **kwargs)
            if creating:
                StatusEvent.objects.create(
                    request=self,
                    from_status="",
                    to_status=self.status,
                    changed_by=self.submitted_by,
                    note="Request logged.",
                )

    def validate_transition(self, new_status, by):
        if new_status not in RequestStatus.values:
            raise ValidationError("Choose a valid lifecycle status.")
        if self.status == new_status:
            return
        current_index = STATUS_ORDER.index(self.status)
        if current_index == len(STATUS_ORDER) - 1 or STATUS_ORDER[current_index + 1] != new_status:
            raise ValidationError("Requests must move through each lifecycle stage in order.")

        coordinator = bool(by and by.can_coordinate)
        delivery = getattr(self, "delivery", None)
        responder = bool(by and by.can_support and delivery and delivery.responder_id == by.pk)
        owner = bool(by and by.is_active and self.submitted_by_id == by.pk)
        allowed = coordinator
        if new_status in (RequestStatus.IN_PROGRESS, RequestStatus.DELIVERED):
            allowed = coordinator or responder
        elif new_status == RequestStatus.CLOSED:
            allowed = coordinator or owner
        if not allowed:
            raise PermissionDenied("Your account cannot make this workflow change.")

        if new_status == RequestStatus.VERIFIED:
            latest = self.latest_verification
            if not latest or latest.decision != "verified":
                raise ValidationError("Record an authorized verification before advancing this request.")
        if new_status in (RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS, RequestStatus.DELIVERED):
            if not delivery:
                raise ValidationError("Assign a support pledge before advancing this request.")
        if new_status == RequestStatus.DELIVERED and not (
            delivery.delivered_at and delivery.recipient_name.strip() and delivery.confirmation_note.strip()
        ):
            raise ValidationError("Record the recipient and hand-over confirmation before marking delivery complete.")
        if new_status == RequestStatus.CLOSED and not (
            delivery and delivery.recipient_confirmed_at and delivery.confirmed_by_id
        ):
            raise ValidationError("Recipient confirmation is required before closing this request.")

    def acknowledge(self, by, at=None):
        """A review is meaningful staff action even when it asks for more information."""
        if not by.can_coordinate:
            raise PermissionDenied("Only authorized staff can acknowledge requests.")
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            fields = ["updated_at"]
            if current.acknowledged_at is None:
                current.acknowledged_at = at or timezone.now()
                fields.append("acknowledged_at")
            models.Model.save(current, update_fields=fields)
            self.acknowledged_at = current.acknowledged_at
            self.updated_at = current.updated_at

    def transition_to(self, new_status, by=None, note=""):
        """Lock the current row and commit the status and audit event together."""
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            current.validate_transition(new_status, by)
            if current.status == new_status:
                self.status = current.status
                return None
            event = StatusEvent.objects.create(
                request=current,
                from_status=current.status,
                to_status=new_status,
                changed_by=by,
                note=note,
            )
            current.status = new_status
            fields = ["status", "updated_at"]
            if current.acknowledged_at is None:
                current.acknowledged_at = event.changed_at
                fields.append("acknowledged_at")
            if new_status == RequestStatus.CLOSED:
                current.closed_at = event.changed_at
                fields.append("closed_at")
            models.Model.save(current, update_fields=fields)
            for field in ("status", "acknowledged_at", "closed_at", "updated_at"):
                setattr(self, field, getattr(current, field))
            self._prefetched_objects_cache = {}
            return event

    @property
    def latest_verification(self):
        return next(iter(self.verifications.all()), None)

    @property
    def verification_state(self):
        latest = self.latest_verification
        return latest.decision if latest else "pending"

    # --- Lifecycle helpers used by the UI -----------------------------------
    @property
    def status_index(self):
        try:
            return STATUS_ORDER.index(self.status)
        except ValueError:
            return 0

    @property
    def progress_percent(self):
        return round(self.status_index / (len(STATUS_ORDER) - 1) * 100)

    @property
    def urgency_weight(self):
        return URGENCY_WEIGHT.get(self.urgency, 9)

    @property
    def is_closed(self):
        return self.status == RequestStatus.CLOSED

    @property
    def tracker_stages(self):
        """[(status, label, caption, state, event_or_None)] for the progress tracker."""
        events = {e.to_status: e for e in self.events.all()}
        current = self.status_index
        stages = []
        for index, status in enumerate(STATUS_ORDER):
            if index < current:
                state = "done"
            elif index == current:
                state = "current"
            else:
                state = "todo"
            stages.append(
                {
                    "status": status,
                    "label": RequestStatus(status).label,
                    "caption": STATUS_CAPTIONS[status],
                    "state": state,
                    "event": events.get(status),
                }
            )
        return stages

    # --- The metric ---------------------------------------------------------
    @property
    def acknowledgement_delta(self):
        if not self.acknowledged_at:
            return None
        return self.acknowledged_at - self.submitted_at

    @property
    def acknowledgement_minutes(self):
        delta = self.acknowledgement_delta
        return delta.total_seconds() / 60 if delta is not None else None

    @property
    def waiting_minutes(self):
        """Minutes since submission for a request that is still unacknowledged."""
        if self.acknowledged_at or not self.submitted_at:
            return None
        return (timezone.now() - self.submitted_at).total_seconds() / 60

    @property
    def target_minutes(self):
        return settings.ACKNOWLEDGEMENT_TARGET_HOURS * 60

    @property
    def acknowledged_within_target(self):
        minutes = self.acknowledgement_minutes
        return None if minutes is None else minutes <= self.target_minutes

    @property
    def is_overdue(self):
        minutes = self.waiting_minutes
        return minutes is not None and minutes > self.target_minutes

    @property
    def acknowledgement_display(self):
        """Human string for the metric, e.g. '18 min' / '3 h 05 m' / 'waiting'."""
        minutes = self.acknowledgement_minutes
        if minutes is None:
            waiting = self.waiting_minutes
            return f"waiting {format_minutes(waiting)}" if waiting is not None else "—"
        return format_minutes(minutes)


def format_minutes(minutes):
    """Compact duration: '42 s', '18 min', '3 h 05 m', '2 d 04 h'."""
    if minutes is None:
        return "—"
    if minutes < 1:
        return f"{int(minutes * 60)} s"
    if minutes < 60:
        return f"{int(minutes)} min"
    hours, rem = divmod(int(minutes), 60)
    if hours < 24:
        return f"{hours} h {rem:02d} m"
    days, hours = divmod(hours, 24)
    return f"{days} d {hours:02d} h"


class StatusEvent(models.Model):
    """One timestamped hop along the lifecycle — the audit trail."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(
        ReliefRequest,
        on_delete=models.CASCADE,
        related_name="events",
    )
    from_status = models.CharField(max_length=20, choices=RequestStatus.choices, blank=True)
    to_status = models.CharField(max_length=20, choices=RequestStatus.choices)
    note = models.CharField(max_length=240, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["changed_at"]
        verbose_name = "status event"

    def __str__(self):
        origin = RequestStatus(self.from_status).label if self.from_status else "new"
        return f"{self.request_id} · {origin} → {RequestStatus(self.to_status).label}"

    @property
    def to_status_label(self):
        return RequestStatus(self.to_status).label

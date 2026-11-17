"""
The coordination desk retains records and links to the authorized workflow.

Status is read-only here; review, assignment, and delivery actions collect the
records required by the lifecycle services.
"""
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince

from .models import ReliefRequest, RequestStatus, StatusEvent, format_minutes

STATUS_COLOURS = {
    RequestStatus.RECEIVED: "#6f8a93",
    RequestStatus.VERIFIED: "#1fa2b8",
    RequestStatus.ASSIGNED: "#f2a03d",
    RequestStatus.IN_PROGRESS: "#ff8a3d",
    RequestStatus.DELIVERED: "#2fb37f",
    RequestStatus.CLOSED: "#3c5a63",
}

URGENCY_COLOURS = {
    "critical": "#ff5f45",
    "high": "#ff8a3d",
    "medium": "#f2a03d",
    "low": "#6f8a93",
}


def _pill(colour, text):
    return format_html(
        '<span style="background:{}1f;color:{};border:1px solid {}59;padding:2px 9px;'
        'border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.05em;'
        'white-space:nowrap;">{}</span>',
        colour,
        colour,
        colour,
        text,
    )


class StatusEventInline(admin.TabularInline):
    model = StatusEvent
    extra = 0
    can_delete = False
    readonly_fields = ("from_status", "to_status", "note", "changed_by", "changed_at")
    fields = ("changed_at", "from_status", "to_status", "changed_by", "note")
    ordering = ("changed_at",)
    verbose_name_plural = "Lifecycle trail (timestamped)"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReliefRequest)
class ReliefRequestAdmin(admin.ModelAdmin):
    inlines = [StatusEventInline]
    date_hierarchy = "submitted_at"
    list_per_page = 25

    list_display = (
        "reference",
        "status_pill",
        "urgency_pill",
        "category",
        "short_location",
        "people_affected",
        "submitted_display",
        "ack_display",
    )
    list_filter = ("status", "urgency", "category", "submitted_at")
    search_fields = ("reference", "location", "description", "contact_name", "contact_phone")
    ordering = ("-submitted_at",)

    readonly_fields = (
        "id",
        "reference",
        "submitted_at",
        "updated_at",
        "acknowledged_at",
        "closed_at",
        "ack_display",
        "progress_bar",
        "status",
        "workflow_link",
        "request_evidence",
    )

    fieldsets = (
        ("Traceability", {"fields": ("reference", "id", "progress_bar", "status", "workflow_link")}),
        (
            "Request",
            {"fields": ("category", "urgency", "people_affected", "location", "public_area", "latitude", "longitude", "description", "request_evidence")},
        ),
        ("Requester", {"fields": ("submitted_by", "contact_name", "contact_phone")}),
        (
            "Timestamps",
            {
                "fields": (
                    "submitted_at",
                    "acknowledged_at",
                    "ack_display",
                    "updated_at",
                    "closed_at",
                )
            },
        ),
    )

    actions = ("action_verify",)

    @admin.display(description="Supporting evidence")
    def request_evidence(self, obj):
        if not obj.supporting_evidence:
            return "No evidence supplied."
        from django.urls import reverse

        return format_html('<a href="{}">Download request evidence</a>', reverse("requests:evidence", kwargs={"pk": obj.pk}))

    @admin.display(description="Request workflow")
    def workflow_link(self, obj):
        if obj._state.adding:
            return "Save this request to open its workflow."
        from django.urls import reverse

        return format_html('<a href="{}">Review, assign support, or confirm delivery →</a>', reverse("requests:detail", kwargs={"pk": obj.pk}))

    def has_delete_permission(self, request, obj=None):
        return False

    # --- Display helpers ----------------------------------------------------
    @admin.display(description="status", ordering="status")
    def status_pill(self, obj):
        colour = STATUS_COLOURS.get(obj.status, "#6f8a93")
        return _pill(colour, obj.get_status_display().upper())

    @admin.display(description="urgency", ordering="urgency")
    def urgency_pill(self, obj):
        colour = URGENCY_COLOURS.get(obj.urgency, "#6f8a93")
        return _pill(colour, obj.get_urgency_display().upper())

    @admin.display(description="location", ordering="location")
    def short_location(self, obj):
        return obj.location if len(obj.location) <= 38 else obj.location[:36] + "…"

    @admin.display(description="submitted", ordering="submitted_at")
    def submitted_display(self, obj):
        return format_html(
            '<span style="font-family:ui-monospace,SFMono-Regular,Menlo,monospace;">{}</span>'
            '<br><span style="color:#6f8a93;font-size:11px;">{} ago</span>',
            obj.submitted_at.strftime("%d %b %Y · %H:%M:%S"),
            timesince(obj.submitted_at).split(",")[0],
        )

    @admin.display(description="time to ack.", ordering="acknowledged_at")
    def ack_display(self, obj):
        minutes = obj.acknowledgement_minutes
        if minutes is None:
            waiting = obj.waiting_minutes
            overdue = obj.is_overdue
            colour = "#ff5f45" if overdue else "#6f8a93"
            label = f"waiting {format_minutes(waiting)}" if waiting is not None else "—"
            return _pill(colour, label.upper())
        colour = "#2fb37f" if obj.acknowledged_within_target else "#ff5f45"
        suffix = "" if obj.acknowledged_within_target else " · OVER TARGET"
        return _pill(colour, f"{format_minutes(minutes)}{suffix}".upper())

    @admin.display(description="lifecycle")
    def progress_bar(self, obj):
        chunks = []
        for stage in obj.tracker_stages:
            colour = STATUS_COLOURS.get(stage["status"], "#6f8a93")
            if stage["state"] == "todo":
                style = "background:#e6ecee;color:#9aa8ab;border:1px dashed #cdd8db;"
            elif stage["state"] == "current":
                style = f"background:{colour};color:#fff;border:1px solid {colour};"
            else:
                style = f"background:{colour}2e;color:{colour};border:1px solid {colour}59;"
            stamp = stage["event"].changed_at.strftime("%d %b %H:%M") if stage["event"] else "—"
            chunks.append(
                format_html(
                    '<div style="flex:1;min-width:104px;padding:6px 8px;border-radius:8px;'
                    'font-size:11px;font-weight:700;letter-spacing:.04em;{}">{}'
                    '<div style="font-weight:500;opacity:.85;font-family:ui-monospace,Menlo,'
                    'monospace;margin-top:3px;">{}</div></div>',
                    style,
                    stage["label"].upper(),
                    stamp,
                )
            )
        return format_html(
            '<div style="display:flex;gap:6px;flex-wrap:wrap;max-width:860px;">{}</div>',
            mark_safe("".join(chunks)),  # each chunk was built with format_html
        )

    # Assignment and delivery use the dedicated forms to collect required records.
    @admin.action(description="Mark selected as Verified")
    def action_verify(self, request, queryset):
        from apps.verification.services import review_request

        if not request.user.can_coordinate:
            raise PermissionDenied("Only authorized staff can verify requests.")
        moved = 0
        for relief_request in queryset:
            try:
                review_request(relief_request.pk, by=request.user, decision="verified", method="document",
                               notes="Verified by authorized staff from the coordination desk.")
            except ValidationError:
                continue
            moved += 1
        self.message_user(request, f"{moved} request(s) verified; {queryset.count() - moved} already beyond review.", messages.SUCCESS)


@admin.register(StatusEvent)
class StatusEventAdmin(admin.ModelAdmin):
    list_display = ("changed_at", "request", "from_status", "to_status", "changed_by")
    list_filter = ("to_status", "changed_at")
    search_fields = ("request__reference", "note")
    readonly_fields = ("id", "request", "from_status", "to_status", "note", "changed_by", "changed_at")
    date_hierarchy = "changed_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

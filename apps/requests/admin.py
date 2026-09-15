"""
Admin = the NGO coordination desk for this milestone.

Status changes made here go through `ReliefRequest.transition_to()`, so the
audit trail and the acknowledgement timestamp stay correct no matter whether a
row is edited in the form or bulk-updated with an action.
"""
from django.contrib import admin, messages
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
    )

    fieldsets = (
        ("Traceability", {"fields": ("reference", "id", "progress_bar", "status")}),
        (
            "Request",
            {"fields": ("category", "urgency", "people_affected", "location", "description")},
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

    actions = (
        "action_verify",
        "action_assign",
        "action_in_progress",
        "action_deliver",
        "action_close",
    )

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

    # --- Keep transitions auditable ----------------------------------------
    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data:
            previous = ReliefRequest.objects.get(pk=obj.pk).status
            new_status = obj.status
            obj.status = previous  # transition_to() writes the change itself
            obj.transition_to(new_status, by=request.user, note="Updated from the admin.")
            # Persist any other edits made on the same form submission.
            super().save_model(request, obj, form, change)
            return
        super().save_model(request, obj, form, change)

    def _bulk_transition(self, request, queryset, status):
        moved = 0
        for relief_request in queryset:
            if relief_request.transition_to(
                status, by=request.user, note="Bulk update from the admin."
            ):
                moved += 1
        label = RequestStatus(status).label
        self.message_user(
            request,
            f"{moved} request(s) moved to “{label}”. "
            f"{queryset.count() - moved} were already there.",
            messages.SUCCESS,
        )

    @admin.action(description="Mark selected as Verified")
    def action_verify(self, request, queryset):
        self._bulk_transition(request, queryset, RequestStatus.VERIFIED)

    @admin.action(description="Mark selected as Assigned")
    def action_assign(self, request, queryset):
        self._bulk_transition(request, queryset, RequestStatus.ASSIGNED)

    @admin.action(description="Mark selected as In progress")
    def action_in_progress(self, request, queryset):
        self._bulk_transition(request, queryset, RequestStatus.IN_PROGRESS)

    @admin.action(description="Mark selected as Delivered")
    def action_deliver(self, request, queryset):
        self._bulk_transition(request, queryset, RequestStatus.DELIVERED)

    @admin.action(description="Mark selected as Closed")
    def action_close(self, request, queryset):
        self._bulk_transition(request, queryset, RequestStatus.CLOSED)


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

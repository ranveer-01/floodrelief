from django.contrib import admin

from apps.verification.admin import RecordAdmin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(RecordAdmin):
    list_display = ("title", "recipient", "created_at", "read_at")
    list_filter = ("read_at",)
    search_fields = ("title", "recipient__email", "request__reference")
    readonly_fields = tuple(field.name for field in Notification._meta.fields)

from django.contrib import admin

from apps.verification.admin import RecordAdmin

from .models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(RecordAdmin):
    list_display = ("request", "responder", "assigned_at", "delivered_at", "recipient_confirmed_at")
    search_fields = ("request__reference", "responder__email")
    readonly_fields = tuple(field.name for field in Delivery._meta.fields)

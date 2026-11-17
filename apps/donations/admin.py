from django.contrib import admin

from apps.verification.admin import RecordAdmin

from .models import Donation


@admin.register(Donation)
class DonationAdmin(RecordAdmin):
    list_display = ("request", "donor", "kind", "quantity", "unit", "status", "pledged_at")
    list_filter = ("kind", "status")
    search_fields = ("request__reference", "donor__email", "description")
    readonly_fields = tuple(field.name for field in Donation._meta.fields)

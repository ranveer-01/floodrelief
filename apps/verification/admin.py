from django.contrib import admin

from .models import Verification


class RecordAdmin(admin.ModelAdmin):
    """Workflow records are created through authorized actions and retained."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Verification)
class VerificationAdmin(RecordAdmin):
    list_display = ("request", "decision", "method", "reviewed_by", "reviewed_at")
    list_filter = ("decision", "method")
    search_fields = ("request__reference", "notes")
    readonly_fields = tuple(field.name for field in Verification._meta.fields)

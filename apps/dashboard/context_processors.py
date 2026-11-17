from django.conf import settings


def notification_count(request):
    user = request.user
    return {"unread_notification_count": user.notifications.filter(read_at__isnull=True).count() if user.is_authenticated else 0}


def platform_settings(request):
    return {"acknowledgement_target_hours": settings.ACKNOWLEDGEMENT_TARGET_HOURS}

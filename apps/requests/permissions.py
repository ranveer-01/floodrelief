from .models import RequestStatus


def can_view_request(user, relief_request):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.can_coordinate or relief_request.submitted_by_id == user.pk:
        return True
    if user.can_support and relief_request.status == RequestStatus.VERIFIED:
        return True
    return relief_request.donations.filter(donor=user).exists()

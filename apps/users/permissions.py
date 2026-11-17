from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def coordinator_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.can_coordinate:
            raise PermissionDenied("Only authorized relief staff can use this page.")
        return view(request, *args, **kwargs)

    return wrapped


def supporter_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.can_support:
            raise PermissionDenied("Your account needs approval before you can offer support.")
        return view(request, *args, **kwargs)

    return wrapped

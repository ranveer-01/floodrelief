"""Account oversight using the same permissions as Django administration."""
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .models import Role, User


def account_summary():
    return User.objects.aggregate(
        total=Count("pk"),
        pending_donors=Count("pk", filter=Q(is_active=True, role__name=Role.Name.DONOR, support_approved=False)),
        approved_donors=Count("pk", filter=Q(is_active=True, role__name=Role.Name.DONOR, support_approved=True)),
        coordinators=Count("pk", filter=Q(is_active=True) & (Q(role__name__in=[Role.Name.NGO_STAFF, Role.Name.ADMIN]) | Q(is_superuser=True))),
    )


def account_filters(data):
    role = data.get("role", "")
    status = data.get("status", "pending")
    return {
        "q": data.get("q", "").strip()[:120],
        "role": role if role in Role.Name.values else "",
        "status": status if status in ("pending", "approved", "active", "inactive", "all") else "pending",
    }


@login_required
@require_GET
@never_cache
def manage_accounts(request):
    if not request.user.can_view_accounts:
        raise PermissionDenied("Account management requires administration permissions.")
    filters = account_filters(request.GET)
    accounts = User.objects.select_related("role").order_by("name", "email")
    if filters["q"]:
        accounts = accounts.filter(Q(name__icontains=filters["q"]) | Q(email__icontains=filters["q"]))
    if filters["role"]:
        accounts = accounts.filter(role__name=filters["role"])
    if filters["status"] == "pending":
        accounts = accounts.filter(is_active=True, role__name=Role.Name.DONOR, support_approved=False)
    elif filters["status"] == "approved":
        accounts = accounts.filter(is_active=True, role__name=Role.Name.DONOR, support_approved=True)
    elif filters["status"] in ("active", "inactive"):
        accounts = accounts.filter(is_active=filters["status"] == "active")
    return render(request, "users/manage_accounts.html", {
        "page_id": "accounts", "filters": filters, "account_stats": account_summary(),
        "role_choices": [(value, "Beneficiary" if value == Role.Name.VICTIM else label) for value, label in Role.Name.choices],
        "page_obj": Paginator(accounts, 20).get_page(request.GET.get("page")),
    })


@login_required
@require_POST
@never_cache
def approve_donor(request, pk):
    if not request.user.can_approve_donors:
        raise PermissionDenied("Donor approval requires permission to change user accounts.")
    with transaction.atomic():
        donor = get_object_or_404(User.objects.select_for_update(), pk=pk, role__name=Role.Name.DONOR, is_active=True)
        if not donor.support_approved:
            donor.support_approved = True
            # Keep the existing post-save notification and after-commit behavior.
            donor.save(update_fields=["support_approved"])
            messages.success(request, f"{donor.name} can now offer support.")
        else:
            messages.info(request, f"{donor.name} already has support approval.")
    return redirect(reverse("users:manage_accounts") + "?" + urlencode(account_filters(request.POST)))

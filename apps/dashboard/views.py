"""Public information and role-scoped relief workspaces."""
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.db.models import Count, OuterRef, Q, Subquery
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.urls import reverse

from apps.requests.models import (
    STATUS_CAPTIONS,
    STATUS_ORDER,
    ReliefRequest,
    RequestStatus,
)

from .models import Notification


class LandingView(TemplateView):
    template_name = "dashboard/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_id"] = "landing"
        context["stats"] = ReliefRequest.objects.acknowledgement_stats()
        context["recent_requests"] = (
            ReliefRequest.objects.select_related("submitted_by").prefetch_related("events")[:3]
        )
        context["lifecycle"] = [
            {
                "index": index + 1,
                "status": status,
                "label": RequestStatus(status).label,
                "caption": STATUS_CAPTIONS[status],
            }
            for index, status in enumerate(STATUS_ORDER)
        ]
        return context


@login_required
def home(request):
    from apps.delivery.models import Delivery
    from apps.users.account_views import account_summary
    from apps.users.models import Role, User
    from apps.verification.models import Verification

    user = request.user
    my_requests = user.relief_requests.prefetch_related("verifications")
    my_pledges = user.donations.select_related("request")[:4]
    deliveries = Delivery.objects.select_related("request", "responder", "donation").exclude(request__status=RequestStatus.CLOSED)
    if not user.can_coordinate:
        deliveries = deliveries.filter(responder=user)
    context = {"page_id": "dashboard", "my_requests": my_requests[:6], "my_pledges": my_pledges,
               "deliveries": deliveries[:4], "available_requests": ReliefRequest.objects.none(),
               "workspace_role": user.workspace_role}
    context["my_request_stats"] = my_requests.aggregate(
        total=Count("pk"),
        active=Count("pk", filter=~Q(status=RequestStatus.CLOSED)),
        awaiting_confirmation=Count("pk", filter=Q(status=RequestStatus.DELIVERED)),
    )
    context["my_pledge_count"] = user.donations.count()
    context["active_delivery_count"] = deliveries.count()
    context["available_count"] = 0
    if user.can_support:
        available = ReliefRequest.objects.filter(status=RequestStatus.VERIFIED).prioritized()
        context["available_requests"] = available.prefetch_related("verifications")[:4]
        context["available_count"] = available.count()
    if user.can_coordinate:
        latest = Verification.objects.filter(request_id=OuterRef("pk")).values("decision")[:1]
        review_requests = ReliefRequest.objects.filter(status=RequestStatus.RECEIVED).annotate(latest_decision=Subquery(latest)).filter(Q(latest_decision__isnull=True) | Q(latest_decision="pending"))
        context["review_count"] = review_requests.count()
        context["review_requests"] = review_requests.prioritized().prefetch_related("verifications")[:4]
        context["stats"] = ReliefRequest.objects.acknowledgement_stats()
        completed = Delivery.objects.filter(delivered_at__isnull=False)
        total = completed.count()
        confirmed = completed.filter(recipient_confirmed_at__isnull=False).count()
        context["delivery_stats"] = {"completed": total, "confirmed": confirmed, "coverage": round(confirmed / total * 100) if total else None}
        counts = dict(ReliefRequest.objects.values_list("status").annotate(n=Count("pk")))
        context["status_counts"] = [{"label": RequestStatus(status).label, "count": counts.get(status, 0)} for status in STATUS_ORDER]
        context["summary_total"] = max(context["stats"]["total"], 1)
    if user.can_view_accounts:
        context["account_stats"] = account_summary()
        context["pending_donors"] = User.objects.filter(is_active=True, role__name=Role.Name.DONOR, support_approved=False).select_related("role").order_by("created_at", "pk")[:4]

    def metric(label, value, hint, url="", format=""):
        return {"label": label, "value": value, "hint": hint, "url": url, "format": format}

    activity_url = reverse("dashboard:activity")
    inbox_url = reverse("dashboard:notifications") + "?unread=1"
    role = user.workspace_role
    if role == Role.Name.ADMIN:
        context.update(dashboard_heading="Platform", dashboard_emphasis="overview.",
                       dashboard_intro="Oversee accounts, donor approvals and relief operations.",
                       primary_label="Manage accounts" if user.can_view_accounts else "View operations",
                       primary_url=reverse("users:manage_accounts") if user.can_view_accounts else activity_url + "?scope=all",
                       primary_icon="people", secondary_label="Relief operations", secondary_url=activity_url + "?scope=all")
        if user.can_view_accounts:
            counts = context["account_stats"]
            accounts_url = reverse("users:manage_accounts")
            context["dashboard_metrics"] = [
                metric("Platform accounts", counts["total"], "Browse accounts", accounts_url + "?status=all"),
                metric("Donors awaiting approval", counts["pending_donors"], "Review approvals", accounts_url),
                metric("Approved donors", counts["approved_donors"], "View approved donors", accounts_url + "?status=approved"),
                metric("Active coordinators", counts["coordinators"], "Staff and administrators"),
            ]
        else:
            context["dashboard_metrics"] = [
                metric("Relief requests", context["stats"]["total"], "Browse operations", activity_url + "?scope=all"),
                metric("Ready for review", context["review_count"], "Open review queue", reverse("verification:queue")),
                metric("Active deliveries", context["active_delivery_count"], "Follow deliveries", activity_url + "?kind=deliveries&scope=all"),
                metric("Unread updates", user.notifications.filter(read_at__isnull=True).count(), "Open notifications", inbox_url),
            ]
    elif role == Role.Name.NGO_STAFF:
        context.update(dashboard_heading="Relief", dashboard_emphasis="coordination.",
                       dashboard_intro="Review incoming needs, assign support and keep deliveries moving.",
                       primary_label="Open review queue", primary_url=reverse("verification:queue"), primary_icon="check",
                       secondary_label="Follow deliveries", secondary_url=activity_url + "?kind=deliveries&scope=all")
        context["dashboard_metrics"] = [
            metric("Ready for review", context["review_count"], "Open queue", reverse("verification:queue")),
            metric("Ready for assignment", context["available_count"], "Review verified needs", activity_url + "?status=verified&scope=all"),
            metric("Active deliveries", context["active_delivery_count"], "Follow deliveries", activity_url + "?kind=deliveries&scope=all"),
            metric("Past acknowledgement target", context["stats"]["breaching"], f'{context["stats"]["awaiting"]} awaiting first action'),
        ]
    elif role == Role.Name.DONOR:
        context.update(dashboard_heading="Your support,", dashboard_emphasis="tracked.",
                       dashboard_intro="Find verified needs, follow your pledges and update the deliveries assigned to you.",
                       primary_label="Find requests to support" if user.can_support else "View approval status",
                       primary_url=reverse("donations:available") if user.can_support else "#donor-status", primary_icon="support",
                       secondary_label="Your pledges", secondary_url=activity_url + "?kind=pledges")
        context["dashboard_metrics"] = [
            metric("Your support pledges", context["my_pledge_count"], "View pledges", activity_url + "?kind=pledges"),
            metric("Your active deliveries", context["active_delivery_count"], "Follow deliveries", activity_url + "?kind=deliveries"),
            metric("Requests awaiting support", context["available_count"] if user.can_support else None,
                   "Browse verified needs" if user.can_support else "Available after approval",
                   reverse("donations:available") if user.can_support else ""),
            metric("Unread updates", user.notifications.filter(read_at__isnull=True).count(), "Open notifications", inbox_url),
        ]
    else:
        context.update(dashboard_heading="Your relief", dashboard_emphasis="requests.",
                       dashboard_intro="Request help, respond to reviews and confirm when support reaches you.",
                       primary_label="Request help", primary_url=reverse("requests:create"), primary_icon="plus",
                       secondary_label="Your requests", secondary_url=activity_url + "?kind=requests")
        counts = context["my_request_stats"]
        context["dashboard_metrics"] = [
            metric("Your requests", counts["total"], "View requests", activity_url + "?kind=requests"),
            metric("Active requests", counts["active"], "From submission to receipt"),
            metric("Awaiting receipt confirmation", counts["awaiting_confirmation"], "Check deliveries", activity_url + "?kind=requests&status=delivered"),
            metric("Unread updates", user.notifications.filter(read_at__isnull=True).count(), "Open notifications", inbox_url),
        ]
    return render(request, "dashboard/home.html", context)


@login_required
def activity(request):
    from apps.delivery.models import Delivery
    from apps.donations.models import Donation

    default_kind = "pledges" if request.user.workspace_role == "donor" else "requests"
    kind = request.GET.get("kind", default_kind)
    if kind not in ("requests", "pledges", "deliveries"):
        kind = default_kind
    all_records = request.user.can_coordinate and request.GET.get("scope", "all") != "mine"
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if kind == "requests":
        records = ReliefRequest.objects.all() if all_records else request.user.relief_requests.all()
        records = records.prefetch_related("verifications")
        choices = RequestStatus.choices
        if query:
            records = records.filter(Q(reference__icontains=query) | Q(location__icontains=query) | Q(category__icontains=query))
        status_field = "status"
    elif kind == "pledges":
        records = Donation.objects.all() if all_records else request.user.donations.all()
        records = records.select_related("request", "donor")
        choices = Donation.Status.choices
        if query:
            records = records.filter(Q(request__reference__icontains=query) | Q(description__icontains=query))
        status_field = "status"
    else:
        records = Delivery.objects.all() if all_records else request.user.deliveries.all()
        records = records.select_related("request", "responder", "donation")
        choices = [(value, label) for value, label in RequestStatus.choices if value in ("assigned", "in_progress", "delivered", "closed")]
        if query:
            records = records.filter(Q(request__reference__icontains=query) | Q(request__location__icontains=query))
        status_field = "request__status"
    if status in dict(choices):
        records = records.filter(**{status_field: status})
    else:
        status = ""
    record_types = [("requests", "Requests"), ("pledges", "Support pledges"), ("deliveries", "Deliveries")]
    if not request.user.can_coordinate:
        if request.user.workspace_role == "donor":
            record_types = [("pledges", "Your pledges"), ("deliveries", "Your deliveries")]
            if request.user.relief_requests.exists() or kind == "requests":
                record_types.append(("requests", "Requests for help"))
        else:
            record_types = [("requests", "Your requests")]
    titles = {"requests": "Relief requests" if all_records else "Your requests",
              "pledges": "Support pledges" if all_records else "Your support pledges",
              "deliveries": "Relief deliveries" if all_records else "Your deliveries"}
    return render(request, "dashboard/activity.html", {
        "page_id": "activity", "kind": kind, "query": query, "status": status,
        "status_choices": choices, "all_records": all_records, "record_types": record_types,
        "activity_title": titles[kind],
        "page_obj": Paginator(records, 20).get_page(request.GET.get("page")),
    })


@login_required
def notifications(request):
    unread_only = request.GET.get("unread") == "1"
    records = request.user.notifications.select_related("request")
    if unread_only:
        records = records.filter(read_at__isnull=True)
    return render(request, "dashboard/notifications.html", {
        "page_id": "notifications", "unread_only": unread_only,
        "page_obj": Paginator(records, 20).get_page(request.GET.get("page")),
    })


@login_required
@require_POST
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    Notification.objects.filter(pk=notification.pk, read_at__isnull=True).update(read_at=timezone.now())
    return redirect("dashboard:notifications")


@login_required
@require_POST
def mark_all_notifications_read(request):
    request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    return redirect("dashboard:notifications")

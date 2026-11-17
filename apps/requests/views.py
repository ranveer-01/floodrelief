"""Public views: submit a request, and track every request."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Case, Count, IntegerField, Max, Q, Value, When
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, ListView
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.cache import never_cache

from .forms import ReliefRequestForm
from .permissions import can_view_request
from .models import (
    STATUS_ORDER,
    Category,
    ReliefRequest,
    RequestStatus,
    URGENCY_WEIGHT,
    Urgency,
)


class RequestCreateView(CreateView):
    """`/requests/new/` — the ModelForm page."""

    model = ReliefRequest
    form_class = ReliefRequestForm
    template_name = "requests/request_form.html"

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        if user.is_authenticated:
            initial.setdefault("contact_name", user.name)
            initial.setdefault("contact_phone", user.phone)
        return initial

    def form_valid(self, form):
        relief_request = form.save(commit=False)
        if self.request.user.is_authenticated:
            relief_request.submitted_by = self.request.user
        if relief_request.supporting_evidence:
            relief_request.evidence_name = relief_request.supporting_evidence.name[:255]
        relief_request.save()  # save() also writes the first StatusEvent
        self.object = relief_request

        messages.success(
            self.request,
            f"Request {relief_request.reference} is logged and on the board.",
        )
        # Skip ModelFormMixin.form_valid: the object is already saved above,
        # with submitted_by attached. Go straight to the board.
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Almost there — a few fields still need attention.")
        return super().form_invalid(form)

    def get_success_url(self):
        if self.request.user.is_authenticated:
            return reverse("requests:detail", kwargs={"pk": self.object.pk})
        return (
            f"{reverse('requests:list')}?highlight={self.object.pk}#req-{self.object.pk}"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_id"] = "submit"
        context["target_hours"] = settings.ACKNOWLEDGEMENT_TARGET_HOURS
        context["stages"] = [
            {"status": status, "label": RequestStatus(status).label} for status in STATUS_ORDER
        ]
        return context


@login_required
def supporting_evidence(request, pk):
    relief_request = get_object_or_404(ReliefRequest, pk=pk)
    if not (request.user.can_coordinate or relief_request.submitted_by_id == request.user.pk):
        raise Http404
    if not relief_request.supporting_evidence:
        raise Http404
    try:
        return FileResponse(
            relief_request.supporting_evidence.open("rb"), as_attachment=True,
            filename=relief_request.evidence_name, content_type="application/octet-stream",
        )
    except FileNotFoundError:
        raise Http404("The evidence file is unavailable.")


def board_revision():
    stats = ReliefRequest.objects.aggregate(total=Count("pk"), latest=Max("updated_at"))
    latest = stats["latest"].isoformat() if stats["latest"] else ""
    return f"{stats['total']}:{latest}"


@require_GET
@never_cache
def board_updates(request):
    return JsonResponse({"revision": board_revision()})


@login_required
@require_GET
@never_cache
def request_updates(request, pk):
    relief_request = get_object_or_404(ReliefRequest, pk=pk)
    if not can_view_request(request.user, relief_request):
        raise Http404
    return JsonResponse({
        "revision": relief_request.updated_at.isoformat(),
        "status": relief_request.status, "label": relief_request.get_status_display(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def request_detail(request, pk):
    from apps.delivery.forms import AssignmentForm, DeliveryConfirmationForm, ReceiptConfirmationForm
    from apps.delivery.services import assign_pledge, confirm_delivery, confirm_receipt, start_delivery
    from apps.donations.forms import DonationForm
    from apps.donations.services import pledge_support
    from apps.verification.forms import ReviewForm, ReviewResponseForm
    from apps.verification.services import respond_to_review, review_request

    relief_request = get_object_or_404(
        ReliefRequest.objects.select_related("submitted_by", "delivery__responder", "delivery__donation", "delivery__confirmed_by")
        .prefetch_related("events__changed_by", "verifications__reviewed_by"), pk=pk,
    )
    if not can_view_request(request.user, relief_request):
        raise Http404
    user = request.user
    owner = relief_request.submitted_by_id == user.pk
    delivery = getattr(relief_request, "delivery", None)
    manages_delivery = user.can_coordinate or bool(delivery and delivery.responder_id == user.pk and user.can_support)
    action = request.POST.get("action", "") if request.method == "POST" else ""
    latest = relief_request.latest_verification
    def form_args(name):
        return {"data": request.POST if action == name else None, "files": request.FILES if action == name else None,
                "auto_id": f"id_{name}_%s"}
    forms = {
        "review": ReviewForm(**form_args("review"), initial={"revision": str(latest.pk) if latest else ""}),
        "respond": ReviewResponseForm(**form_args("respond")),
        "pledge": DonationForm(**form_args("pledge")),
        "assign": AssignmentForm(**form_args("assign"), relief_request=relief_request),
        "deliver": DeliveryConfirmationForm(**form_args("deliver")),
        "confirm": ReceiptConfirmationForm(**form_args("confirm")),
    }
    if request.method == "POST":
        permissions = {"review": user.can_coordinate, "respond": owner, "pledge": user.can_support,
                       "assign": user.can_coordinate, "start": manages_delivery, "deliver": manages_delivery,
                       "confirm": owner or user.can_coordinate}
        if action not in permissions:
            return HttpResponseBadRequest("Choose a valid request action.")
        if not permissions[action]:
            raise PermissionDenied("Your account cannot perform this action.")
        form = forms.get(action)
        if form is None or form.is_valid():
            data = form.cleaned_data if form else {}
            try:
                if action == "review":
                    review_request(pk, by=user, decision=data["decision"], method=data["method"], notes=data["notes"],
                                   evidence=data["evidence"], expected_revision=data["revision"])
                elif action == "respond":
                    respond_to_review(pk, by=user, **data)
                elif action == "pledge":
                    pledge_support(pk, by=user, **data)
                elif action == "assign":
                    assign_pledge(pk, by=user, donation_id=data["pledge"].pk)
                elif action == "start":
                    start_delivery(pk, by=user)
                elif action == "deliver":
                    confirm_delivery(pk, by=user, **data)
                elif action == "confirm":
                    confirm_receipt(pk, by=user, **data)
            except ValidationError as error:
                if form:
                    form.add_error(None, " ".join(error.messages))
                messages.error(request, " ".join(error.messages))
            else:
                messages.success(request, {"review": "Review decision recorded.", "respond": "Additional information sent for review.",
                                          "pledge": "Support pledge recorded.", "assign": "Support assigned to the responder.",
                                          "start": "Delivery is now in progress.", "deliver": "Hand-over recorded. Awaiting recipient confirmation.",
                                          "confirm": "Receipt confirmed. This request is now closed."}[action])
                return redirect("requests:detail", pk=pk)

    donations = relief_request.donations.select_related("donor")
    if not (owner or user.can_coordinate):
        donations = donations.filter(donor=user)
    duplicates = ReliefRequest.objects.none()
    if user.can_coordinate and relief_request.status == RequestStatus.RECEIVED:
        duplicates = ReliefRequest.objects.filter(category=relief_request.category, location__iexact=relief_request.location).exclude(pk=pk).exclude(status=RequestStatus.CLOSED)[:5]
    return render(request, "requests/request_detail.html", {
        "page_id": "request", "relief_request": relief_request, "delivery": delivery, "forms": forms,
        "donations": donations, "duplicates": duplicates, "owner": owner,
        "private_details": owner or user.can_coordinate or bool(delivery and delivery.responder_id == user.pk),
        "can_review": user.can_coordinate and relief_request.status == RequestStatus.RECEIVED,
        "can_respond": owner and relief_request.status == RequestStatus.RECEIVED and relief_request.verification_state == "more_info",
        "can_pledge": user.can_support and relief_request.status == RequestStatus.VERIFIED,
        "can_assign": user.can_coordinate and relief_request.status == RequestStatus.VERIFIED,
        "can_start": bool(delivery) and manages_delivery and relief_request.status == RequestStatus.ASSIGNED,
        "can_deliver": bool(delivery) and manages_delivery and relief_request.status == RequestStatus.IN_PROGRESS,
        "can_confirm": (owner or user.can_coordinate) and relief_request.status == RequestStatus.DELIVERED and delivery is not None,
    })


class RequestListView(ListView):
    """`/requests/` — the live board, with the lifecycle visible per request."""

    model = ReliefRequest
    template_name = "requests/request_list.html"
    context_object_name = "relief_requests"
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            ReliefRequest.objects.select_related("submitted_by")
            .prefetch_related("events")
        )

        self.active_status = self.request.GET.get("status", "")
        self.active_urgency = self.request.GET.get("urgency", "")
        self.query = (self.request.GET.get("q") or "").strip()
        self.ordering_mode = self.request.GET.get("sort", "recent")

        if self.active_status in RequestStatus.values:
            queryset = queryset.filter(status=self.active_status)
        if self.active_urgency in Urgency.values:
            queryset = queryset.filter(urgency=self.active_urgency)
        if self.query:
            queryset = queryset.filter(
                Q(reference__icontains=self.query)
                | Q(public_area__icontains=self.query)
                | Q(category__icontains=self.query)
            )

        if self.ordering_mode == "urgency":
            queryset = queryset.annotate(
                urgency_rank=Case(
                    *[
                        When(urgency=value, then=Value(weight))
                        for value, weight in URGENCY_WEIGHT.items()
                    ],
                    default=Value(9),
                    output_field=IntegerField(),
                )
            ).order_by("urgency_rank", "-submitted_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        everything = ReliefRequest.objects.all()

        context["page_id"] = "board"
        context["stats"] = everything.acknowledgement_stats()
        context["highlight_id"] = self.request.GET.get("highlight", "")
        context["active_status"] = self.active_status
        context["active_urgency"] = self.active_urgency
        context["query"] = self.query
        context["ordering_mode"] = self.ordering_mode
        context["board_revision"] = board_revision()
        context["urgency_choices"] = Urgency.choices
        context["category_choices"] = Category.choices

        counts = {
            row["status"]: row["n"] for row in everything.values("status").annotate(n=Count("id"))
        }
        context["status_filters"] = [
            {
                "value": "",
                "label": "All",
                "count": everything.count(),
                "is_active": self.active_status == "",
            }
        ] + [
            {
                "value": status,
                "label": RequestStatus(status).label,
                "count": counts.get(status, 0),
                "is_active": self.active_status == status,
            }
            for status in STATUS_ORDER
        ]
        return context

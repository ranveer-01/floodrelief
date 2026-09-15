"""Public views: submit a request, and track every request."""
from django.contrib import messages
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, ListView

from .forms import ReliefRequestForm
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
        return (
            f"{reverse('requests:list')}?highlight={self.object.pk}#req-{self.object.pk}"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_id"] = "submit"
        context["stages"] = [
            {"status": status, "label": RequestStatus(status).label} for status in STATUS_ORDER
        ]
        return context


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
                | Q(location__icontains=self.query)
                | Q(description__icontains=self.query)
                | Q(contact_name__icontains=self.query)
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

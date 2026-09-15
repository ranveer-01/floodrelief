"""The public landing page."""
from django.views.generic import TemplateView

from apps.requests.models import (
    STATUS_CAPTIONS,
    STATUS_ORDER,
    ReliefRequest,
    RequestStatus,
)


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

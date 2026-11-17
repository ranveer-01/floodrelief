from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Q, Subquery
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator

from apps.requests.models import ReliefRequest, RequestStatus
from apps.users.permissions import coordinator_required

from .models import Verification


@coordinator_required
def queue(request):
    decision = request.GET.get("decision", "pending")
    if decision not in (*Verification.Decision.values, "all"):
        decision = "pending"
    query = request.GET.get("q", "").strip()
    latest = Verification.objects.filter(request_id=OuterRef("pk")).values("decision")[:1]
    requests = ReliefRequest.objects.filter(status=RequestStatus.RECEIVED).annotate(latest_decision=Subquery(latest))
    if decision == "pending":
        requests = requests.filter(Q(latest_decision__isnull=True) | Q(latest_decision="pending"))
    elif decision != "all":
        requests = requests.filter(latest_decision=decision)
    if query:
        requests = requests.filter(Q(reference__icontains=query) | Q(location__icontains=query) | Q(contact_name__icontains=query))
    page = Paginator(requests.prioritized().prefetch_related("verifications"), 12).get_page(request.GET.get("page"))
    return render(request, "verification/queue.html", {
        "page_id": "verification", "page_obj": page, "decision": decision, "query": query,
        "decision_choices": [("pending", "Pending review"), ("more_info", "Needs information"), ("rejected", "Rejected"), ("all", "All reviews")],
    })


@login_required
def evidence(request, pk):
    verification = get_object_or_404(Verification.objects.select_related("request"), pk=pk)
    if not (request.user.can_coordinate or verification.request.submitted_by_id == request.user.pk):
        raise Http404
    if not verification.evidence:
        raise Http404
    try:
        return FileResponse(verification.evidence.open("rb"), as_attachment=True,
                            filename=verification.evidence_name, content_type="application/octet-stream")
    except FileNotFoundError:
        raise Http404("The evidence file is unavailable.")

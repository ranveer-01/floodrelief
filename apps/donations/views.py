from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.requests.models import ReliefRequest, RequestStatus
from apps.users.permissions import supporter_required

from .models import Donation
from .services import withdraw_pledge


@supporter_required
def available(request):
    query = request.GET.get("q", "").strip()
    requests = ReliefRequest.objects.filter(status=RequestStatus.VERIFIED)
    if query:
        area_search = Q(public_area__icontains=query)
        if request.user.can_coordinate:
            area_search |= Q(location__icontains=query)
        requests = requests.filter(Q(reference__icontains=query) | area_search | Q(category__icontains=query))
    page = Paginator(requests.prioritized().prefetch_related("verifications"), 12).get_page(request.GET.get("page"))
    return render(request, "donations/available.html", {"page_id": "support", "page_obj": page, "query": query})


@login_required
@require_POST
def withdraw(request, pk):
    donation = get_object_or_404(Donation, pk=pk, donor=request.user)
    try:
        withdraw_pledge(donation.pk, by=request.user)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Your support pledge was withdrawn.")
    return redirect("requests:detail", pk=donation.request_id)

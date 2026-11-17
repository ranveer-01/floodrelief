from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from .models import Delivery


@login_required
def proof(request, pk):
    delivery = get_object_or_404(Delivery.objects.select_related("request"), pk=pk)
    if not (request.user.can_coordinate or request.user.pk in (delivery.responder_id, delivery.request.submitted_by_id)):
        raise Http404
    if not delivery.proof:
        raise Http404
    try:
        return FileResponse(delivery.proof.open("rb"), as_attachment=True,
                            filename=delivery.proof_name, content_type="application/octet-stream")
    except FileNotFoundError:
        raise Http404("The proof file is unavailable.")

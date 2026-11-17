"""Public map data contains only verified needs and approximate area positions."""
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import render
from django.urls import reverse

from apps.requests.models import Category, ReliefRequest, RequestStatus, Urgency


ACTIVE_MAP_STATUSES = (RequestStatus.VERIFIED, RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS, RequestStatus.DELIVERED)


def request_map(request):
    requests = ReliefRequest.objects.filter(status__in=ACTIVE_MAP_STATUSES)
    category = request.GET.get("category", "")
    urgency = request.GET.get("urgency", "")
    if category in Category.values:
        requests = requests.filter(category=category)
    else:
        category = ""
    if urgency in Urgency.values:
        requests = requests.filter(urgency=urgency)
    else:
        urgency = ""
    total = requests.count()
    rows = []
    for item in requests.prioritized().values("reference", "public_area", "category", "urgency", "status", "people_affected", "latitude", "longitude")[:250]:
        # Round before serializing; never put original coordinates or free-text
        # descriptions, addresses, names, or attachment metadata in the page.
        rows.append({
            "reference": item["reference"], "area": item["public_area"] or "Area shared privately",
            "category": Category(item["category"]).label, "urgency": Urgency(item["urgency"]).label,
            "status": RequestStatus(item["status"]).label, "people": item["people_affected"],
            "latitude": round(float(item["latitude"]), 2) if item["latitude"] is not None else None,
            "longitude": round(float(item["longitude"]), 2) if item["longitude"] is not None else None,
            "url": reverse("requests:list") + "?" + urlencode({"q": item["reference"]}),
        })
    located = sum(row["latitude"] is not None and row["longitude"] is not None for row in rows)
    return render(request, "dashboard/map.html", {
        "page_id": "map", "map_requests": rows, "total": total, "located": located,
        "map_enabled": bool(settings.GOOGLE_MAPS_API_KEY and located), "maps_key": settings.GOOGLE_MAPS_API_KEY,
        "category": category, "urgency": urgency, "category_choices": Category.choices, "urgency_choices": Urgency.choices,
    })

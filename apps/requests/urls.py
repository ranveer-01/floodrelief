from django.urls import path

from .views import RequestCreateView, RequestListView, board_updates, request_detail, request_updates, supporting_evidence

app_name = "requests"

urlpatterns = [
    path("", RequestListView.as_view(), name="list"),
    path("new/", RequestCreateView.as_view(), name="create"),
    path("updates/", board_updates, name="board_updates"),
    path("<uuid:pk>/evidence/", supporting_evidence, name="evidence"),
    path("<uuid:pk>/updates/", request_updates, name="updates"),
    path("<uuid:pk>/", request_detail, name="detail"),
]

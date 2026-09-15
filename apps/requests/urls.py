from django.urls import path

from .views import RequestCreateView, RequestListView

app_name = "requests"

urlpatterns = [
    path("", RequestListView.as_view(), name="list"),
    path("new/", RequestCreateView.as_view(), name="create"),
]

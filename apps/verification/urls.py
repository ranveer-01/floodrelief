from django.urls import path

from . import views

app_name = "verification"

urlpatterns = [
    path("", views.queue, name="queue"),
    path("<uuid:pk>/evidence/", views.evidence, name="evidence"),
]

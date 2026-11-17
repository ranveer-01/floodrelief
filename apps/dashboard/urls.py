from django.urls import path

from . import views
from .maps import request_map

app_name = "dashboard"

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("map/", request_map, name="map"),
    path("dashboard/", views.home, name="home"),
    path("dashboard/activity/", views.activity, name="activity"),
    path("dashboard/notifications/", views.notifications, name="notifications"),
    path("dashboard/notifications/read-all/", views.mark_all_notifications_read, name="read_all"),
    path("dashboard/notifications/<uuid:pk>/read/", views.mark_notification_read, name="read_notification"),
]

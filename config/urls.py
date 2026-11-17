"""Root URL configuration for FloodRelief Connect."""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "FloodRelief Connect — Coordination Desk"
admin.site.site_title = "FloodRelief Connect"
admin.site.index_title = "Relief operations"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.users.urls")),
    path("", include("apps.dashboard.urls")),
    path("requests/", include("apps.requests.urls")),
    path("verification/", include("apps.verification.urls")),
    path("support/", include("apps.donations.urls")),
    path("delivery/", include("apps.delivery.urls")),
]

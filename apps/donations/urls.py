from django.urls import path

from . import views

app_name = "donations"

urlpatterns = [
    path("", views.available, name="available"),
    path("<uuid:pk>/withdraw/", views.withdraw, name="withdraw"),
]

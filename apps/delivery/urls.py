from django.urls import path

from . import views

app_name = "delivery"

urlpatterns = [path("<uuid:pk>/proof/", views.proof, name="proof")]

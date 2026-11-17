from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import SignInView, register
from .account_views import approve_donor, manage_accounts

app_name = "users"

urlpatterns = [
    path("manage/", manage_accounts, name="manage_accounts"),
    path("manage/<uuid:pk>/approve/", approve_donor, name="approve_donor"),
    path("login/", SignInView.as_view(), name="login"),
    path("register/", register, name="register"),
    path("logout/", LogoutView.as_view(next_page="dashboard:landing"), name="logout"),
]

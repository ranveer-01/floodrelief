from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import EmailAuthenticationForm, RegistrationForm
from .models import Role


class SignInView(LoginView):
    template_name = "users/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True
    extra_context = {"page_id": "account"}


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save(commit=False)
                user.role, _ = Role.objects.get_or_create(name=form.cleaned_data["role"])
                user.save()
        except IntegrityError:
            form.add_error("email", "An account already uses this email address.")
        else:
            login(request, user)
            messages.success(request, "Your account is ready.")
            return redirect("dashboard:home")
    return render(request, "users/register.html", {"form": form, "page_id": "account"})

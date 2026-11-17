from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm

from .models import Role, User


def style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, (forms.HiddenInput, forms.CheckboxInput)):
            continue
        field.widget.attrs["class"] = "field__input"
        if field.required:
            field.widget.attrs["aria-required"] = "true"


class RegistrationForm(BaseUserCreationForm):
    role = forms.ChoiceField(
        choices=[(Role.Name.VICTIM, "I need relief"), (Role.Name.DONOR, "I want to offer support")],
        label="How will you use the platform?",
        help_text="Donors need administrator approval before offering support. Staff accounts are created by administrators.",
    )

    class Meta:
        model = User
        fields = ("name", "email", "phone")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Enter the name we should use for your account.")
        return name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email

    def clean_phone(self):
        from apps.requests.forms import PHONE_RE

        phone = self.cleaned_data["phone"].strip()
        if phone and not PHONE_RE.fullmatch(phone):
            raise forms.ValidationError("Enter a reachable phone number.")
        return phone


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address", widget=forms.EmailInput(attrs={"autocomplete": "username"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_username(self):
        email = self.cleaned_data["username"].strip()
        # Also accept case-insensitive login for accounts created through the admin.
        return User.objects.filter(email__iexact=email).values_list("email", flat=True).first() or email.lower()

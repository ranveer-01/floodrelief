"""ModelForm used by the public submission page."""
import re

from django import forms

from .models import Category, ReliefRequest, Urgency

PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{6,18}$")


class ReliefRequestForm(forms.ModelForm):
    """
    Deliberately short — a form filled in on a phone, on a bad connection,
    by someone standing in water. Seven fields, no account required.
    """

    class Meta:
        model = ReliefRequest
        fields = [
            "contact_name",
            "contact_phone",
            "category",
            "urgency",
            "people_affected",
            "location",
            "description",
            "public_area",
            "latitude",
            "longitude",
            "supporting_evidence",
        ]
        labels = {
            "contact_name": "Your name",
            "contact_phone": "Phone number we can reach",
            "category": "What do you need",
            "urgency": "How urgent is it",
            "people_affected": "People affected",
            "location": "Where are you",
            "description": "Describe the situation",
            "public_area": "Public district or town (optional)",
            "latitude": "Latitude (optional)",
            "longitude": "Longitude (optional)",
            "supporting_evidence": "Supporting evidence (optional)",
        }
        help_texts = {
            "contact_phone": "Used only to confirm this request and coordinate delivery.",
            "location": "Village or ward, nearest landmark, district.",
            "people_affected": "Rough count is fine.",
            "description": "What is needed, for how many, and anything a responder must know.",
            "public_area": "Shown on the public board. Use a district or town; keep your address and contact details in the location field.",
            "latitude": "Between -90 and 90. Map positions are rounded to show the approximate area.",
            "longitude": "Between -180 and 180. Enter both coordinates or leave both empty.",
            "supporting_evidence": "JPEG, PNG or PDF, up to 5 MB. Available only to you and authorized review staff.",
        }
        widgets = {
            "contact_name": forms.TextInput(
                attrs={"placeholder": "e.g. Anjali Barman", "autocomplete": "name"}
            ),
            "contact_phone": forms.TextInput(
                attrs={"placeholder": "e.g. +91 98xxxxxx21", "autocomplete": "tel", "inputmode": "tel"}
            ),
            "category": forms.Select(),
            "urgency": forms.RadioSelect(attrs={"class": "segmented__input"}),
            "people_affected": forms.NumberInput(attrs={"min": 1, "max": 5000, "inputmode": "numeric"}),
            "location": forms.TextInput(
                attrs={"placeholder": "e.g. Ward 4, near the old jute mill, Barpeta"}
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "e.g. Six families on the school roof since last night. "
                        "Two elderly, one infant. Drinking water and dry food needed."
                    ),
                    "data-counter": "true",
                    "maxlength": 1200,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [("", "Select a category…")] + list(Category.choices)
        self.fields["urgency"].initial = Urgency.HIGH
        self.fields["people_affected"].initial = 1
        self.fields["people_affected"].min_value = 1
        self.fields["people_affected"].max_value = 5000
        self.fields["description"].max_length = 1200

        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                continue
            css = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{css} field__input".strip()
            if field.required:
                widget.attrs["aria-required"] = "true"

    def clean_contact_phone(self):
        phone = (self.cleaned_data["contact_phone"] or "").strip()
        if not PHONE_RE.fullmatch(phone):
            raise forms.ValidationError(
                "Enter a reachable phone number — digits only, with or without a country code."
            )
        return phone

    def clean_contact_name(self):
        name = (self.cleaned_data["contact_name"] or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter the name we should ask for.")
        return name

    def clean_location(self):
        location = (self.cleaned_data["location"] or "").strip()
        if len(location) < 4:
            raise forms.ValidationError(
                "Add enough detail for a responder to find you — a landmark helps."
            )
        return location

    def clean_description(self):
        description = (self.cleaned_data["description"] or "").strip()
        if len(description) < 15:
            raise forms.ValidationError(
                "Tell us a little more — what is needed and for how many people."
            )
        if len(description) > 1200:
            raise forms.ValidationError("Keep the description within 1200 characters.")
        return description

    def clean_people_affected(self):
        people = self.cleaned_data["people_affected"]
        if not 1 <= people <= 5000:
            raise forms.ValidationError("Enter a number between 1 and 5000.")
        return people

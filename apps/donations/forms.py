from django import forms

from apps.users.forms import style_fields

from .models import Donation


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ("kind", "description", "quantity", "unit")
        labels = {"kind": "Type of support", "description": "What can you provide?", "quantity": "Amount or quantity", "unit": "Unit"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "quantity": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"})}
        help_texts = {"quantity": "For funds, enter the amount in INR. This records a pledge; no payment is collected."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if len(description) < 10:
            raise forms.ValidationError("Describe the support you can provide in at least 10 characters.")
        return description

    def clean(self):
        data = super().clean()
        if data.get("kind") == Donation.Kind.FUNDS:
            if data.get("unit", "").strip().upper() != "INR":
                self.add_error("unit", "Use INR as the unit for a funds pledge.")
            else:
                data["unit"] = "INR"
        return data

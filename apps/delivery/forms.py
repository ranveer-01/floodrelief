from django import forms

from apps.donations.models import Donation
from apps.requests.files import validate_evidence
from apps.users.forms import style_fields


class PledgeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, pledge):
        return f"{pledge.donor.name} · {pledge.quantity} {pledge.unit} · {pledge.description[:80]}"


class AssignmentForm(forms.Form):
    pledge = PledgeChoiceField(queryset=Donation.objects.none(), label="Choose a support pledge",
                              help_text="Assign one approved responder to coordinate this request's delivery.")

    def __init__(self, *args, relief_request, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pledge"].queryset = relief_request.donations.filter(status=Donation.Status.PLEDGED).select_related("donor", "donor__role")
        style_fields(self)


class DeliveryConfirmationForm(forms.Form):
    recipient_name = forms.CharField(min_length=2, max_length=120, label="Who received the support?")
    confirmation_note = forms.CharField(min_length=10, max_length=2000, label="Hand-over confirmation",
                                        widget=forms.Textarea(attrs={"rows": 4}),
                                        help_text="Record what was delivered, when, and how the recipient confirmed the hand-over.")
    proof = forms.FileField(required=False, validators=[validate_evidence], label="Proof of delivery",
                           help_text="Optional JPEG, PNG or PDF, up to 5 MB. Shared only with the requester, assigned responder and staff.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class ReceiptConfirmationForm(forms.Form):
    confirmed = forms.BooleanField(label="I confirm that the support reached the recipient.")
    notes = forms.CharField(min_length=10, max_length=2000, label="Recipient confirmation",
                           widget=forms.Textarea(attrs={"rows": 3}),
                           help_text="Requesters can confirm here. Staff must record the recipient's confirmation by phone or in person.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

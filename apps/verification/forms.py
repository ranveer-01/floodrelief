from django import forms

from apps.requests.files import validate_evidence
from apps.users.forms import style_fields

from .models import Verification


class ReviewForm(forms.Form):
    decision = forms.ChoiceField(choices=[choice for choice in Verification.Decision.choices if choice[0] != "pending"])
    method = forms.ChoiceField(choices=[choice for choice in Verification.Method.choices if choice[0] != "requester"])
    notes = forms.CharField(min_length=10, max_length=2000, widget=forms.Textarea(attrs={"rows": 4}),
                            help_text="Record how you checked the request, or what information is missing. Visible to the requester and staff.")
    evidence = forms.FileField(required=False, validators=[validate_evidence], help_text="Optional JPEG, PNG or PDF, up to 5 MB. Private to the requester and staff.")
    revision = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class ReviewResponseForm(forms.Form):
    notes = forms.CharField(label="Additional information", min_length=10, max_length=2000,
                            widget=forms.Textarea(attrs={"rows": 4}),
                            help_text="Answer the reviewer's questions. Your request will return to the review queue.")
    evidence = forms.FileField(required=False, validators=[validate_evidence], help_text="Optional JPEG, PNG or PDF, up to 5 MB.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

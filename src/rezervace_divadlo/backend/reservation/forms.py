from django import forms
from django.contrib.auth import get_user_model


class SeatSelectionForm(forms.Form):
    """Only currently available seats are valid choices."""

    seats = forms.TypedMultipleChoiceField(
        coerce=int,
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": "Vyberte alespoň jedno sedadlo.",
            "invalid_choice": "Vybrané sedadlo už není dostupné.",
        },
    )

    def __init__(self, *args, available_seat_ids, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["seats"].choices = [(seat_id, seat_id) for seat_id in available_seat_ids]


class ContactForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

from django import forms
from django.core.exceptions import ValidationError

from accounts.models import User, UserRole
from teams.models import Team


class TeamEditForm(forms.ModelForm):
    captain = forms.ModelChoiceField(
        queryset=User.objects.filter(role=UserRole.CAPTAIN).order_by("username"),
        required=False,
    )

    class Meta:
        model = Team
        fields = ["name", "logo", "colors", "motto", "captain", "captain_player"]

    def __init__(self, *args, tournament=None, allow_captain_change=True, **kwargs):
        super().__init__(*args, **kwargs)
        if tournament is not None:
            self.fields["captain"].queryset = User.objects.filter(role=UserRole.CAPTAIN).order_by("username")
            self.fields["captain_player"].queryset = tournament.players.order_by("name")
        if not allow_captain_change:
            self.fields.pop("captain")
            self.fields.pop("captain_player")

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        if not name:
            raise ValidationError("Team name is required.")
        return cleaned_data

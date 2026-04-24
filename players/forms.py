from django import forms

from players.models import Player
from tournaments.models import SportType

CRICKET_POSITIONS = [
    ("", "Select position"),
    ("Batter", "Batter"),
    ("Bowler", "Bowler"),
    ("Allrounder", "Allrounder"),
    ("Wicket Keeper", "Wicket Keeper"),
]

FOOTBALL_POSITIONS = [
    ("", "Select position"),
    ("Forward", "Forward"),
    ("Midfield", "Midfield"),
    ("Defender", "Defender"),
    ("Goal Keeper", "Goal Keeper"),
]


def position_choices_for_sport(sport_type: str):
    if sport_type == SportType.CRICKET:
        return CRICKET_POSITIONS
    return FOOTBALL_POSITIONS


class PlayerUploadForm(forms.Form):
    file = forms.FileField(help_text="Upload a CSV file with either player rows or a comma-separated list of player names.")


class PlayerCreateForm(forms.ModelForm):
    role_position = forms.ChoiceField(required=False)

    class Meta:
        model = Player
        fields = ["name", "role_position", "base_price", "age", "city", "notes", "profile_image"]

    def __init__(self, *args, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        sport_type = tournament.sport_type if tournament else SportType.CRICKET
        self.fields["role_position"].choices = position_choices_for_sport(sport_type)
        self.fields["name"].required = True
        self.fields["base_price"].required = True
        self.fields["age"].required = False


class PlayerEditForm(forms.ModelForm):
    role_position = forms.ChoiceField(required=False)

    class Meta:
        model = Player
        fields = ["profile_image", "role_position", "city", "notes"]

    def __init__(self, *args, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        sport_type = tournament.sport_type if tournament else SportType.CRICKET
        self.fields["role_position"].choices = position_choices_for_sport(sport_type)

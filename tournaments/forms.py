from django import forms

from accounts.models import User
from tournaments.models import TeamSelectionMethod, Tournament


class DateInput(forms.DateInput):
    input_type = "date"


class TournamentForm(forms.ModelForm):
    assigned_admins = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role="admin").order_by("username"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    auctioneer = forms.ModelChoiceField(
        queryset=User.objects.filter(role="admin").order_by("username"),
        required=False,
    )

    class Meta:
        model = Tournament
        fields = [
            "sport_type",
            "logo",
            "name",
            "description",
            "start_date",
            "number_of_teams",
            "playing_members",
            "total_members",
            "purse_default",
            "first_prize",
            "second_prize",
            "third_prize",
            "participation_amount",
            "team_selection_method",
            "auctioneer",
            "timer_seconds",
            "min_increment",
            "currency_label",
            "assigned_admins",
        ]
        widgets = {
            "start_date": DateInput(),
        }
        labels = {
            "start_date": "Tournament date",
            "playing_members": "Playing members",
            "total_members": "Total squad members",
            "purse_default": "Default purse",
        }

    def clean(self):
        cleaned_data = super().clean()
        selection_method = cleaned_data.get("team_selection_method")
        auctioneer = cleaned_data.get("auctioneer")
        assigned_admins = cleaned_data.get("assigned_admins")
        if selection_method == TeamSelectionMethod.AUCTION and not auctioneer:
            self.add_error("auctioneer", "Choose an auctioneer when team selection uses auction.")
        if auctioneer and assigned_admins and auctioneer not in assigned_admins:
            self.add_error("auctioneer", "Auctioneer must also be one of the selected admins.")
        return cleaned_data

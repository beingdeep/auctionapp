from datetime import datetime, time, timedelta

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User, UserRole


class AuctionAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_captain() and not user.temporary_password_is_valid():
            raise ValidationError("This captain password has expired. Ask an admin to reset it.")


class AdminUserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), help_text="Temporary password for the new admin.")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "password"]

    def save(self, commit=True, created_by=None):
        user = super().save(commit=False)
        user.role = UserRole.ADMIN
        user.created_by = created_by
        user.is_staff = False
        user.is_superuser = False
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CaptainCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), help_text="Temporary password for the captain.")
    team_slot = forms.IntegerField(min_value=1)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "password", "team_slot"]

    def __init__(self, *args, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tournament = tournament

    def clean_team_slot(self):
        team_slot = self.cleaned_data["team_slot"]
        if self.tournament and not self.tournament.teams.filter(team_slot=team_slot).exists():
            raise ValidationError("Pick a valid team slot for this tournament.")
        return team_slot

    def save(self, commit=True, created_by=None):
        user = super().save(commit=False)
        user.role = UserRole.CAPTAIN
        user.created_by = created_by
        if self.tournament:
            expires_on = self.tournament.start_date + timedelta(days=1)
            user.temp_password_expires_at = timezone.make_aware(datetime.combine(expires_on, time.max))
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

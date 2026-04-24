from django.apps import apps
from django.conf import settings
from django.db import models
from django.utils import timezone


class SportType(models.TextChoices):
    CRICKET = "cricket", "Cricket"
    FOOTBALL = "football", "Football"


class TournamentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    LIVE = "live", "Live"
    CLOSED = "closed", "Closed"


class TeamSelectionMethod(models.TextChoices):
    AUCTION = "auction", "By auction"
    SUBMISSION = "submission", "By submission"


class Tournament(models.Model):
    name = models.CharField(max_length=120)
    sport_type = models.CharField(max_length=20, choices=SportType.choices)
    logo = models.FileField(upload_to="tournament_logos/", blank=True)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    status = models.CharField(max_length=20, choices=TournamentStatus.choices, default=TournamentStatus.DRAFT)
    purse_default = models.DecimalField(max_digits=12, decimal_places=2)
    timer_seconds = models.PositiveIntegerField(default=90)
    min_increment = models.DecimalField(max_digits=12, decimal_places=2, default=100)
    currency_label = models.CharField(max_length=10, default="INR")
    number_of_teams = models.PositiveIntegerField(default=2)
    playing_members = models.PositiveIntegerField(default=11)
    total_members = models.PositiveIntegerField(default=15)
    first_prize = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    second_prize = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    third_prize = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    participation_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    team_selection_method = models.CharField(
        max_length=20,
        choices=TeamSelectionMethod.choices,
        default=TeamSelectionMethod.AUCTION,
    )
    assigned_admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_tournaments",
        blank=True,
    )
    auctioneer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="auctioneer_tournaments",
    )

    def __str__(self) -> str:
        return self.name

    def is_past(self) -> bool:
        return self.start_date < timezone.localdate()

    def can_be_managed_by(self, user) -> bool:
        if not user or not user.is_authenticated or not user.is_admin():
            return False
        if self.is_past() and not user.is_super_admin():
            return False
        return True

    def sync_team_slots(self) -> None:
        Team = apps.get_model("teams", "Team")
        current_slots = set(self.teams.values_list("team_slot", flat=True))
        for slot in range(1, self.number_of_teams + 1):
            if slot not in current_slots:
                Team.objects.create(
                    tournament=self,
                    team_slot=slot,
                    name=f"Team {slot}",
                    purse_remaining=self.purse_default,
                )

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, UniqueConstraint

from tournaments.models import Tournament


class Team(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="teams")
    captain = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="teams",
    )
    team_slot = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=120, blank=True)
    logo = models.FileField(upload_to="team_logos/", blank=True)
    colors = models.CharField(max_length=120, blank=True)
    motto = models.CharField(max_length=255, blank=True)
    captain_player = models.ForeignKey(
        "players.Player",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="captain_for_teams",
    )
    purse_remaining = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["tournament", "team_slot"], name="unique_team_slot_per_tournament"),
            UniqueConstraint(
                fields=["tournament", "captain"],
                condition=Q(captain__isnull=False),
                name="unique_captain_per_tournament",
            ),
            UniqueConstraint(
                fields=["tournament", "captain_player"],
                condition=Q(captain_player__isnull=False),
                name="unique_captain_player_per_tournament",
            ),
        ]

    def clean(self) -> None:
        if self.purse_remaining < Decimal("0"):
            raise ValidationError("Purse cannot be negative")

    def __str__(self) -> str:
        return self.name or f"Team {self.team_slot}"

    def roster_count(self) -> int:
        return self.players.count()

    def remaining_slots(self) -> int:
        return max(self.tournament.total_members - self.roster_count(), 0)

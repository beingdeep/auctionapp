from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from tournaments.models import Tournament


class Team(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="teams")
    captain = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team")
    name = models.CharField(max_length=120)
    logo = models.URLField(blank=True)
    purse_remaining = models.DecimalField(max_digits=12, decimal_places=2)

    def clean(self) -> None:
        if self.purse_remaining < Decimal("0"):
            raise ValidationError("Purse cannot be negative")

    def __str__(self) -> str:
        return self.name

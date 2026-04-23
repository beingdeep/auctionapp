from django.core.validators import MinValueValidator
from django.db import models

from tournaments.models import SportType, Tournament


class PlayerStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    SOLD = "sold", "Sold"
    UNSOLD = "unsold", "Unsold"


class Player(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="players")
    name = models.CharField(max_length=120)
    sport_type = models.CharField(max_length=20, choices=SportType.choices)
    role_position = models.CharField(max_length=80)
    age = models.PositiveIntegerField()
    base_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    city = models.CharField(max_length=80, blank=True)
    team_history = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=PlayerStatus.choices, default=PlayerStatus.AVAILABLE)

    class Meta:
        unique_together = ("tournament", "name", "sport_type", "role_position", "age")

    def __str__(self) -> str:
        return self.name

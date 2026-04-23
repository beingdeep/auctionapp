from django.db import models


class SportType(models.TextChoices):
    CRICKET = "cricket", "Cricket"
    FOOTBALL = "football", "Football"


class TournamentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    LIVE = "live", "Live"
    CLOSED = "closed", "Closed"


class Tournament(models.Model):
    name = models.CharField(max_length=120)
    sport_type = models.CharField(max_length=20, choices=SportType.choices)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    status = models.CharField(max_length=20, choices=TournamentStatus.choices, default=TournamentStatus.DRAFT)
    purse_default = models.DecimalField(max_digits=12, decimal_places=2)
    timer_seconds = models.PositiveIntegerField(default=90)
    min_increment = models.DecimalField(max_digits=12, decimal_places=2, default=100)
    currency_label = models.CharField(max_length=10, default="INR")

    def __str__(self) -> str:
        return self.name

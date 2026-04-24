from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from players.models import Player, PlayerStatus
from teams.models import Team
from tournaments.models import Tournament


class RoundStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    CLOSED = "closed", "Closed"


class AuctionRound(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="rounds")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="rounds")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=RoundStatus.choices, default=RoundStatus.PENDING)
    winning_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="won_rounds")
    winning_bid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def is_timer_expired(self) -> bool:
        return bool(self.end_time and timezone.now() >= self.end_time)

    def current_highest_bid(self):
        return self.bids.order_by("-amount", "timestamp").first()

    @transaction.atomic
    def finalize(self) -> None:
        highest_bid = self.bids.select_for_update().order_by("-amount", "timestamp").first()
        self.status = RoundStatus.CLOSED
        self.closed_at = timezone.now()
        if highest_bid is None:
            self.player.status = PlayerStatus.UNSOLD
            self.player.save(update_fields=["status"])
            self.save(update_fields=["status", "closed_at"])
            return

        team = Team.objects.select_for_update().get(id=highest_bid.team_id)
        if team.purse_remaining < highest_bid.amount:
            raise ValidationError("Insufficient purse for winning team")
        if team.remaining_slots() <= 0:
            raise ValidationError("Winning team has no remaining player slots")

        team.purse_remaining -= highest_bid.amount
        team.full_clean()
        team.save(update_fields=["purse_remaining"])

        self.winning_team = team
        self.winning_bid = highest_bid.amount
        self.player.status = PlayerStatus.SOLD
        self.player.assigned_team = team
        self.player.sold_for = highest_bid.amount
        self.player.save(update_fields=["status", "assigned_team", "sold_for"])
        self.save(update_fields=["status", "closed_at", "winning_team", "winning_bid"])

    @transaction.atomic
    def mark_unsold(self) -> None:
        if self.bids.exists():
            raise ValidationError("This player already has bids. Use Sold instead.")
        self.status = RoundStatus.CLOSED
        self.closed_at = timezone.now()
        self.player.status = PlayerStatus.UNSOLD
        self.player.save(update_fields=["status"])
        self.save(update_fields=["status", "closed_at"])


class Bid(models.Model):
    auction_round = models.ForeignKey(AuctionRound, on_delete=models.CASCADE, related_name="bids")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="bids")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def clean(self) -> None:
        if self.auction_round.status != RoundStatus.ACTIVE:
            raise ValidationError("Round is not active")
        if self.auction_round.is_timer_expired():
            raise ValidationError("Timer ended")

        highest_bid = self.auction_round.bids.exclude(pk=self.pk).order_by("-amount").first()
        current_price = highest_bid.amount if highest_bid else self.auction_round.player.base_price

        if self.amount <= current_price:
            raise ValidationError("Bid must be greater than current highest bid")

        if self.team.purse_remaining < self.amount:
            raise ValidationError("Insufficient purse")

        if self.team.remaining_slots() <= 0:
            raise ValidationError("No squad slots remaining for this team")

        if highest_bid and highest_bid.team_id == self.team_id and highest_bid.amount == self.amount:
            raise ValidationError("Duplicate spam bid blocked")

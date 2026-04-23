from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, UserRole
from auction.models import AuctionRound, Bid, RoundStatus
from players.models import Player, PlayerStatus
from teams.models import Team
from tournaments.models import SportType, Tournament


class AuctionRulesTestCase(TestCase):
    def setUp(self):
        self.tournament = Tournament.objects.create(
            name="Summer League",
            sport_type=SportType.CRICKET,
            description="",
            start_date=timezone.now().date(),
            purse_default=Decimal("1000"),
            timer_seconds=90,
            min_increment=Decimal("50"),
        )
        self.cap1 = User.objects.create_user(username="cap1", password="x", role=UserRole.CAPTAIN)
        self.cap2 = User.objects.create_user(username="cap2", password="x", role=UserRole.CAPTAIN)
        self.team1 = Team.objects.create(tournament=self.tournament, captain=self.cap1, name="Team A", purse_remaining=Decimal("1000"))
        self.team2 = Team.objects.create(tournament=self.tournament, captain=self.cap2, name="Team B", purse_remaining=Decimal("1000"))
        self.player = Player.objects.create(
            tournament=self.tournament,
            name="P1",
            sport_type=SportType.CRICKET,
            role_position="Batsman",
            age=22,
            base_price=Decimal("100"),
        )
        self.round = AuctionRound.objects.create(
            tournament=self.tournament,
            player=self.player,
            status=RoundStatus.ACTIVE,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(seconds=30),
        )

    def test_bid_validation_increment(self):
        bid = Bid(auction_round=self.round, team=self.team1, amount=Decimal("120"))
        with self.assertRaises(ValidationError):
            bid.clean()

    def test_purse_deduction_on_finalize(self):
        bid = Bid(auction_round=self.round, team=self.team1, amount=Decimal("150"))
        bid.full_clean()
        bid.save()
        self.round.finalize()
        self.team1.refresh_from_db()
        self.player.refresh_from_db()
        self.assertEqual(self.team1.purse_remaining, Decimal("850"))
        self.assertEqual(self.player.status, PlayerStatus.SOLD)

    def test_concurrent_bids_highest_wins(self):
        b1 = Bid(auction_round=self.round, team=self.team1, amount=Decimal("150"))
        b1.full_clean(); b1.save()
        b2 = Bid(auction_round=self.round, team=self.team2, amount=Decimal("200"))
        b2.full_clean(); b2.save()
        self.round.finalize()
        self.round.refresh_from_db()
        self.assertEqual(self.round.winning_team_id, self.team2.id)
        self.assertEqual(self.round.winning_bid, Decimal("200"))

    def test_timer_close_logic(self):
        self.round.end_time = timezone.now() - timedelta(seconds=1)
        self.round.save(update_fields=["end_time"])
        bid = Bid(auction_round=self.round, team=self.team1, amount=Decimal("150"))
        with self.assertRaises(ValidationError):
            bid.clean()

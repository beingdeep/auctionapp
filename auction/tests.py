from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, UserRole
from auction.models import AuctionRound, Bid, RoundStatus
from auction.services import all_captains_online, auction_state, equally_distribute_unsold_players, place_bid, select_random_player
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
        self.team1 = Team.objects.create(
            tournament=self.tournament,
            captain=self.cap1,
            team_slot=1,
            name="Team A",
            purse_remaining=Decimal("1000"),
        )
        self.team2 = Team.objects.create(
            tournament=self.tournament,
            captain=self.cap2,
            team_slot=2,
            name="Team B",
            purse_remaining=Decimal("1000"),
        )
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

    def test_bid_must_beat_current_price(self):
        bid = Bid(auction_round=self.round, team=self.team1, amount=Decimal("100"))
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


class LiveAuctionServiceTests(TestCase):
    def setUp(self):
        self.tournament = Tournament.objects.create(
            name="Live League",
            sport_type=SportType.CRICKET,
            start_date=timezone.localdate(),
            purse_default=Decimal("10000"),
            timer_seconds=90,
            min_increment=Decimal("1000"),
            total_members=4,
        )
        self.auctioneer = User.objects.create_user(username="auctioneer", password="pw", role=UserRole.ADMIN)
        self.cap1 = User.objects.create_user(
            username="captain1",
            password="pw",
            role=UserRole.CAPTAIN,
            last_seen_at=timezone.now(),
        )
        self.cap2 = User.objects.create_user(
            username="captain2",
            password="pw",
            role=UserRole.CAPTAIN,
            last_seen_at=timezone.now(),
        )
        self.cap_player1 = Player.objects.create(
            tournament=self.tournament,
            name="Captain Player One",
            sport_type=SportType.CRICKET,
            base_price=Decimal("1000"),
        )
        self.cap_player2 = Player.objects.create(
            tournament=self.tournament,
            name="Captain Player Two",
            sport_type=SportType.CRICKET,
            base_price=Decimal("1000"),
        )
        self.target_player = Player.objects.create(
            tournament=self.tournament,
            name="Auction Target",
            sport_type=SportType.CRICKET,
            base_price=Decimal("1000"),
        )
        self.team1 = Team.objects.create(
            tournament=self.tournament,
            captain=self.cap1,
            captain_player=self.cap_player1,
            team_slot=1,
            name="Team A",
            purse_remaining=Decimal("10000"),
        )
        self.team2 = Team.objects.create(
            tournament=self.tournament,
            captain=self.cap2,
            captain_player=self.cap_player2,
            team_slot=2,
            name="Team B",
            purse_remaining=Decimal("10000"),
        )
        self.tournament.auctioneer = self.auctioneer
        self.tournament.save(update_fields=["auctioneer"])

    def test_all_captains_online_detects_ready_lobby(self):
        self.assertTrue(all_captains_online(self.tournament))

    def test_random_selection_excludes_captain_players(self):
        round_obj = select_random_player(self.tournament)

        self.assertEqual(round_obj.player, self.target_player)

    def test_quick_bids_stack_safely_and_sale_assigns_player(self):
        round_obj = select_random_player(self.tournament)

        bid1 = place_bid(self.tournament, self.cap1)
        bid2 = place_bid(self.tournament, self.cap2)
        round_obj.finalize()
        round_obj.refresh_from_db()
        self.target_player.refresh_from_db()

        self.assertEqual(bid1.amount, Decimal("2000"))
        self.assertEqual(bid2.amount, Decimal("3000"))
        self.assertEqual(round_obj.winning_team_id, self.team2.id)
        self.assertEqual(self.target_player.assigned_team_id, self.team2.id)
        self.assertEqual(self.target_player.sold_for, Decimal("3000"))
        self.assertIsNotNone(round_obj.closed_at)

    def test_auction_state_returns_latest_bid_first_and_sold_history(self):
        round_obj = select_random_player(self.tournament)
        place_bid(self.tournament, self.cap1)
        place_bid(self.tournament, self.cap2)

        state_before_sale = auction_state(self.tournament)
        self.assertEqual(state_before_sale["bid_history"][0]["captain_name"], self.cap2.display_name())

        round_obj.finalize()
        state_after_sale = auction_state(self.tournament)
        self.assertEqual(state_after_sale["sold_history"][0]["player_name"], self.target_player.name)

    def test_equal_distribution_uses_available_slots(self):
        team3_captain = User.objects.create_user(
            username="captain3",
            password="pw",
            role=UserRole.CAPTAIN,
            last_seen_at=timezone.now(),
        )
        team3 = Team.objects.create(
            tournament=self.tournament,
            captain=team3_captain,
            team_slot=3,
            name="Team C",
            purse_remaining=Decimal("10000"),
        )
        self.tournament.number_of_teams = 3
        self.tournament.save(update_fields=["number_of_teams"])
        for name, team in [("Roster A1", self.team1), ("Roster B1", self.team2)]:
            Player.objects.create(
                tournament=self.tournament,
                name=name,
                sport_type=SportType.CRICKET,
                assigned_team=team,
                sold_for=Decimal("0"),
                status=PlayerStatus.SOLD,
            )
        for index in range(1, 5):
            Player.objects.create(
                tournament=self.tournament,
                name=f"Unsold {index}",
                sport_type=SportType.CRICKET,
                status=PlayerStatus.UNSOLD,
            )

        self.tournament.total_members = 2
        self.tournament.save(update_fields=["total_members"])

        assigned = equally_distribute_unsold_players(self.tournament)

        self.assertEqual(assigned, 4)
        self.assertEqual(self.team1.players.count(), 2)
        self.assertEqual(self.team2.players.count(), 2)
        self.assertEqual(team3.players.count(), 2)

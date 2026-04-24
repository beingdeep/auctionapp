from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, UserRole
from players.models import Player
from teams.models import Team
from tournaments.models import SportType, TeamSelectionMethod, Tournament


class TournamentFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.super_admin = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="pw",
            role=UserRole.ADMIN,
        )
        self.admin = User.objects.create_user(username="ops", password="pw", role=UserRole.ADMIN)
        self.client.post(reverse("login"), {"username": "root", "password": "pw"})

    def test_admin_can_create_tournament_and_team_slots(self):
        response = self.client.post(
            reverse("tournament-create"),
            {
                "sport_type": SportType.CRICKET,
                "name": "Champions Cup",
                "description": "Main event",
                "start_date": timezone.localdate() + timedelta(days=10),
                "number_of_teams": 3,
                "playing_members": 11,
                "total_members": 15,
                "purse_default": "1000",
                "first_prize": "5000",
                "second_prize": "2500",
                "third_prize": "1000",
                "participation_amount": "300",
                "team_selection_method": TeamSelectionMethod.AUCTION,
                "auctioneer": self.admin.pk,
                "timer_seconds": 90,
                "min_increment": "50",
                "currency_label": "INR",
                "assigned_admins": [self.admin.pk],
            },
        )

        tournament = Tournament.objects.get(name="Champions Cup")
        self.assertRedirects(response, reverse("tournament-detail", kwargs={"pk": tournament.pk}))
        self.assertEqual(tournament.teams.count(), 3)
        self.assertTrue(tournament.assigned_admins.filter(pk=self.super_admin.pk).exists())

    def test_previous_tournament_is_read_only_for_regular_admin(self):
        tournament = Tournament.objects.create(
            name="Old Cup",
            sport_type=SportType.FOOTBALL,
            start_date=timezone.localdate() - timedelta(days=2),
            purse_default=Decimal("1000"),
        )
        tournament.assigned_admins.add(self.admin)
        self.client.logout()
        self.client.post(reverse("login"), {"username": "ops", "password": "pw"})

        response = self.client.get(reverse("tournament-edit", kwargs={"pk": tournament.pk}))

        self.assertEqual(response.status_code, 403)

    def test_csv_import_creates_players(self):
        tournament = Tournament.objects.create(
            name="Import Cup",
            sport_type=SportType.CRICKET,
            start_date=timezone.localdate() + timedelta(days=3),
            purse_default=Decimal("500"),
        )
        csv_file = SimpleUploadedFile(
            "players.csv",
            b"name,preferred position,city\nAlice,Batter,Berlin\nBob,Bowler,Hamburg\n",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("tournament-players", kwargs={"pk": tournament.pk}),
            {"action": "upload", "file": csv_file},
        )

        self.assertRedirects(response, reverse("tournament-players", kwargs={"pk": tournament.pk}))
        self.assertEqual(Player.objects.filter(tournament=tournament).count(), 2)

    def test_simple_comma_separated_name_upload_creates_players(self):
        tournament = Tournament.objects.create(
            name="Name List Cup",
            sport_type=SportType.CRICKET,
            start_date=timezone.localdate() + timedelta(days=3),
            purse_default=Decimal("500"),
        )
        csv_file = SimpleUploadedFile(
            "players.csv",
            b"Alice, Bob, Charlie",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("tournament-players", kwargs={"pk": tournament.pk}),
            {"action": "upload", "file": csv_file},
        )

        self.assertRedirects(response, reverse("tournament-players", kwargs={"pk": tournament.pk}))
        self.assertEqual(
            list(Player.objects.filter(tournament=tournament).order_by("name").values_list("name", flat=True)),
            ["Alice", "Bob", "Charlie"],
        )

    def test_excel_upload_is_rejected(self):
        tournament = Tournament.objects.create(
            name="Import Cup",
            sport_type=SportType.CRICKET,
            start_date=timezone.localdate() + timedelta(days=3),
            purse_default=Decimal("500"),
        )
        fake_excel = SimpleUploadedFile(
            "players.xlsx",
            b"not-really-excel",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            reverse("tournament-players", kwargs={"pk": tournament.pk}),
            {"action": "upload", "file": fake_excel},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload CSV only for now")

    def test_manual_player_create_works(self):
        tournament = Tournament.objects.create(
            name="Manual Cup",
            sport_type=SportType.CRICKET,
            start_date=timezone.localdate() + timedelta(days=3),
            purse_default=Decimal("500"),
        )

        response = self.client.post(
            reverse("tournament-players", kwargs={"pk": tournament.pk}),
            {
                "action": "create_manual",
                "name": "Manual Player",
                "role_position": "Batter",
                "base_price": "1500",
                "age": "24",
                "city": "Berlin",
                "notes": "Added manually",
            },
        )

        self.assertRedirects(response, reverse("tournament-players", kwargs={"pk": tournament.pk}))
        player = Player.objects.get(tournament=tournament, name="Manual Player")
        self.assertEqual(player.sport_type, SportType.CRICKET)
        self.assertEqual(player.role_position, "Batter")
        self.assertEqual(player.base_price, Decimal("1500"))

    def test_captain_can_update_team_before_tournament(self):
        tournament = Tournament.objects.create(
            name="Captain Cup",
            sport_type=SportType.CRICKET,
            start_date=timezone.localdate() + timedelta(days=1),
            purse_default=Decimal("700"),
        )
        captain = User.objects.create_user(username="captain1", password="pw", role=UserRole.CAPTAIN)
        team = Team.objects.create(
            tournament=tournament,
            captain=captain,
            team_slot=1,
            name="Team 1",
            purse_remaining=Decimal("700"),
        )
        self.client.logout()
        self.client.post(reverse("login"), {"username": "captain1", "password": "pw"})

        response = self.client.post(
            reverse("tournament-teams", kwargs={"pk": tournament.pk}),
            {
                "team_id": team.pk,
                "team-{}".format(team.pk) + "-name": "Falcons",
                "team-{}".format(team.pk) + "-colors": "Blue and White",
                "team-{}".format(team.pk) + "-motto": "Play bold",
            },
        )

        self.assertRedirects(response, reverse("tournament-teams", kwargs={"pk": tournament.pk}))
        team.refresh_from_db()
        self.assertEqual(team.name, "Falcons")

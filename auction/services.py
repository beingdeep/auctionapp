from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from auction.models import AuctionRound, Bid, RoundStatus
from players.models import PlayerStatus
from teams.models import Team
from tournaments.models import TournamentStatus


def get_active_round(tournament):
    return tournament.rounds.filter(status=RoundStatus.ACTIVE).select_related("player", "winning_team").first()


def recent_bid_rows(round_obj):
    if not round_obj:
        return []
    return [
        {
            "captain_name": bid.team.captain.display_name() if bid.team.captain else bid.team.name,
            "team_name": bid.team.name,
            "amount": str(bid.amount),
            "timestamp": timezone.localtime(bid.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        }
        for bid in round_obj.bids.select_related("team__captain").order_by("-timestamp")
    ]


def recent_sold_rows(tournament, sort_by="time"):
    rounds = list(
        tournament.rounds.filter(status=RoundStatus.CLOSED, winning_team__isnull=False)
        .select_related("player", "winning_team")
    )
    rows = [
        {
            "player_name": round_obj.player.name,
            "team_name": round_obj.winning_team.name if round_obj.winning_team else "",
            "amount": str(round_obj.winning_bid or 0),
            "amount_value": float(round_obj.winning_bid or 0),
            "timestamp": timezone.localtime(round_obj.closed_at).strftime("%Y-%m-%d %H:%M:%S") if round_obj.closed_at else "",
            "timestamp_value": round_obj.closed_at.isoformat() if round_obj.closed_at else "",
        }
        for round_obj in rounds
    ]
    if sort_by == "amount":
        rows.sort(key=lambda row: (-row["amount_value"], row["timestamp_value"]), reverse=False)
    else:
        rows.sort(key=lambda row: row["timestamp_value"], reverse=True)
    return rows


def get_presence_rows(tournament):
    return [
        {
            "team": team,
            "captain_name": team.captain.display_name() if team.captain else "Captain not assigned",
            "online": bool(team.captain and team.captain.is_online()),
        }
        for team in tournament.teams.select_related("captain").order_by("team_slot")
    ]


def all_captains_online(tournament) -> bool:
    teams = list(tournament.teams.select_related("captain").order_by("team_slot"))
    if len(teams) != tournament.number_of_teams:
        return False
    if any(team.captain_id is None for team in teams):
        return False
    return all(team.captain.is_online() for team in teams if team.captain)


def available_player_queryset(tournament):
    queryset = tournament.players.filter(status=PlayerStatus.AVAILABLE, assigned_team__isnull=True)
    captain_player_ids = list(
        tournament.teams.exclude(captain_player__isnull=True).values_list("captain_player_id", flat=True)
    )
    captain_names = set()
    for team in tournament.teams.select_related("captain"):
        if team.captain:
            captain_names.add(team.captain.display_name().strip())
            captain_names.add(team.captain.username.strip())
    if captain_player_ids:
        queryset = queryset.exclude(pk__in=captain_player_ids)
    captain_names = [name for name in captain_names if name]
    if captain_names:
        queryset = queryset.exclude(name__in=captain_names)
    return queryset


@transaction.atomic
def start_tournament_auction(tournament):
    tournament.status = TournamentStatus.LIVE
    tournament.save(update_fields=["status"])


@transaction.atomic
def select_random_player(tournament):
    if get_active_round(tournament):
        raise ValidationError("Finish the current live round before selecting another player.")

    player = available_player_queryset(tournament).order_by("?").first()
    if not player:
        raise ValidationError("No available players are left in the live pool.")

    now = timezone.now()
    return AuctionRound.objects.create(
        tournament=tournament,
        player=player,
        status=RoundStatus.ACTIVE,
        start_time=now,
        end_time=now + timezone.timedelta(seconds=tournament.timer_seconds),
    )


@transaction.atomic
def place_bid(tournament, captain_user, *, custom_amount=None):
    try:
        round_obj = AuctionRound.objects.select_for_update().select_related("player", "tournament").get(
            tournament=tournament,
            status=RoundStatus.ACTIVE,
        )
    except ObjectDoesNotExist as exc:
        raise ValidationError("No active live round is available right now.") from exc
    if round_obj.is_timer_expired():
        raise ValidationError("The timer has expired for this player.")

    try:
        team = Team.objects.select_for_update().get(tournament=tournament, captain=captain_user)
    except ObjectDoesNotExist as exc:
        raise ValidationError("Only captains assigned to a tournament team can bid.") from exc
    highest = Bid.objects.select_for_update().filter(auction_round=round_obj).order_by("-amount", "timestamp").first()
    current_price = highest.amount if highest else round_obj.player.base_price

    if custom_amount not in (None, ""):
        try:
            amount = Decimal(str(custom_amount))
        except InvalidOperation as exc:
            raise ValidationError("Enter a valid custom bid amount.") from exc
        if amount <= current_price:
            raise ValidationError("Custom bid must be higher than the latest live bid.")
    else:
        amount = current_price + tournament.min_increment

    bid = Bid(auction_round=round_obj, team=team, amount=amount)
    bid.full_clean()
    bid.save()
    round_obj.end_time = timezone.now() + timezone.timedelta(seconds=tournament.timer_seconds)
    round_obj.save(update_fields=["end_time"])
    return bid


def mark_round_sold(tournament):
    round_obj = get_active_round(tournament)
    if not round_obj:
        raise ValidationError("No active round is running.")
    round_obj.finalize()
    return round_obj


def mark_round_unsold(tournament):
    round_obj = get_active_round(tournament)
    if not round_obj:
        raise ValidationError("No active round is running.")
    round_obj.mark_unsold()
    return round_obj


def assign_player_to_team(player, team, sold_for=Decimal("0")):
    if team.remaining_slots() <= 0:
        raise ValidationError(f"{team} has no remaining squad slots.")
    player.assigned_team = team
    player.sold_for = sold_for
    player.status = PlayerStatus.SOLD
    player.save(update_fields=["assigned_team", "sold_for", "status"])


@transaction.atomic
def recycle_unsold_players(tournament):
    return tournament.players.filter(status=PlayerStatus.UNSOLD, assigned_team__isnull=True).update(status=PlayerStatus.AVAILABLE)


@transaction.atomic
def equally_distribute_unsold_players(tournament):
    assigned = 0
    unsold_players = list(tournament.players.filter(status=PlayerStatus.UNSOLD, assigned_team__isnull=True).order_by("name"))
    for player in unsold_players:
        candidate_teams = sorted(
            [team for team in tournament.teams.all() if team.remaining_slots() > 0],
            key=lambda team: (-team.remaining_slots(), team.team_slot),
        )
        if not candidate_teams:
            break
        assign_player_to_team(player, candidate_teams[0], Decimal("0"))
        assigned += 1
    return assigned


@transaction.atomic
def manually_distribute_unsold_players(tournament, team_mapping):
    assigned = 0
    for player in tournament.players.filter(status=PlayerStatus.UNSOLD, assigned_team__isnull=True).order_by("name"):
        team_id = team_mapping.get(str(player.pk))
        if not team_id:
            continue
        team = tournament.teams.get(pk=team_id)
        assign_player_to_team(player, team, Decimal("0"))
        assigned += 1
    return assigned


def auction_state(tournament):
    active_round = get_active_round(tournament)
    highest_bid = active_round.current_highest_bid() if active_round else None
    available_count = available_player_queryset(tournament).count()
    unsold_count = tournament.players.filter(status=PlayerStatus.UNSOLD, assigned_team__isnull=True).count()
    sold_history = recent_sold_rows(tournament)
    return {
        "tournament_name": tournament.name,
        "status": tournament.status,
        "all_captains_online": all_captains_online(tournament),
        "presence_rows": [
            {
                "team_name": row["team"].name or f"Team {row['team'].team_slot}",
                "captain_name": row["captain_name"],
                "online": row["online"],
                "logo_url": row["team"].logo.url if row["team"].logo else "",
            }
            for row in get_presence_rows(tournament)
        ],
        "available_count": available_count,
        "unsold_count": unsold_count,
        "distribution_required": available_count == 0 and unsold_count > 0 and not active_round,
        "bid_history": recent_bid_rows(active_round),
        "sold_history": sold_history,
        "current_round": {
            "player_name": active_round.player.name,
            "player_image": active_round.player.profile_image.url if active_round.player.profile_image else "",
            "base_price": str(active_round.player.base_price),
            "current_bid": str(highest_bid.amount if highest_bid else active_round.player.base_price),
            "current_team": highest_bid.team.name if highest_bid else "",
            "seconds_remaining": max(int((active_round.end_time - timezone.now()).total_seconds()), 0) if active_round.end_time else 0,
            "ends_at": active_round.end_time.isoformat() if active_round.end_time else "",
            "bid_count": active_round.bids.count(),
        }
        if active_round
        else None,
    }

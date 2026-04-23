from django.db.models import Count, Sum

from players.models import PlayerStatus
from teams.models import Team


def tournament_summary(tournament_id: int) -> dict:
    teams = Team.objects.filter(tournament_id=tournament_id)
    aggregate = teams.aggregate(total_purse=Sum("purse_remaining"))
    sold_count = teams.first().tournament.players.filter(status=PlayerStatus.SOLD).count() if teams.exists() else 0
    unsold_count = teams.first().tournament.players.filter(status=PlayerStatus.UNSOLD).count() if teams.exists() else 0
    final_squads = (
        Team.objects.filter(tournament_id=tournament_id)
        .annotate(player_count=Count("won_rounds"))
        .values("name", "purse_remaining", "player_count")
    )
    return {
        "teams": list(teams.values("name", "purse_remaining")),
        "sold_players": sold_count,
        "unsold_players": unsold_count,
        "total_purse_remaining": aggregate["total_purse"],
        "final_squads": list(final_squads),
    }

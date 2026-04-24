from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView
from django.utils import timezone

from accounts.forms import CaptainCreateForm
from teams.forms import TeamEditForm
from teams.models import Team
from tournaments.models import Tournament


class TournamentTeamsView(LoginRequiredMixin, TemplateView):
    template_name = "teams/tournament_teams.html"

    def get_tournament(self):
        return get_object_or_404(Tournament, pk=self.kwargs["pk"])

    def _is_admin(self):
        return self.request.user.is_admin()

    def _captain_team(self, tournament):
        return tournament.teams.filter(captain=self.request.user).first()

    def dispatch(self, request, *args, **kwargs):
        tournament = self.get_tournament()
        if not request.user.is_admin() and not tournament.teams.filter(captain=request.user).exists():
            return HttpResponseForbidden("You do not have access to these teams.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        is_admin = self._is_admin()
        teams = tournament.teams.select_related("captain").order_by("team_slot")
        if not is_admin:
            teams = teams.filter(captain=self.request.user)
        context["tournament"] = tournament
        context["is_admin"] = is_admin
        context["can_captain_edit"] = timezone.localdate() <= tournament.start_date
        context["captain_form"] = kwargs.get("captain_form", CaptainCreateForm(tournament=tournament))
        context["team_cards"] = []
        for team in teams:
            allow_captain_change = is_admin
            context["team_cards"].append(
                {
                    "team": team,
                    "form": kwargs.get(
                        f"team_form_{team.pk}",
                        TeamEditForm(instance=team, tournament=tournament, allow_captain_change=allow_captain_change, prefix=f"team-{team.pk}"),
                    ),
                    "players": team.players.order_by("name"),
                }
            )
        return context

    def post(self, request, *args, **kwargs):
        tournament = self.get_tournament()
        if request.POST.get("action") == "create_captain":
            if not request.user.is_admin():
                return HttpResponseForbidden("Only admins can add captains.")
            captain_form = CaptainCreateForm(request.POST, tournament=tournament)
            if captain_form.is_valid():
                user = captain_form.save(created_by=request.user)
                team = tournament.teams.get(team_slot=captain_form.cleaned_data["team_slot"])
                team.captain = user
                if not team.name:
                    team.name = f"Team {team.team_slot}"
                team.save()
                messages.success(request, f"Captain account created for {user.display_name()}.")
                return redirect("tournament-teams", pk=tournament.pk)
            return self.render_to_response(self.get_context_data(captain_form=captain_form))

        team = get_object_or_404(Team, pk=request.POST.get("team_id"), tournament=tournament)
        is_admin = request.user.is_admin()
        if not is_admin and team.captain_id != request.user.id:
            return HttpResponseForbidden("You can only edit your own team.")
        if not is_admin and timezone.localdate() > tournament.start_date:
            return HttpResponseForbidden("Team setup is locked after the auction date.")

        allow_captain_change = is_admin
        form = TeamEditForm(
            request.POST,
            request.FILES,
            instance=team,
            tournament=tournament,
            allow_captain_change=allow_captain_change,
            prefix=f"team-{team.pk}",
        )
        if form.is_valid():
            updated_team = form.save(commit=False)
            if not is_admin:
                updated_team.captain = request.user
            updated_team.save()
            messages.success(request, f"{updated_team} saved.")
            return redirect("tournament-teams", pk=tournament.pk)

        return self.render_to_response(self.get_context_data(**{f"team_form_{team.pk}": form}))

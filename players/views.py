from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from accounts.views import AdminRequiredMixin
from players.forms import PlayerCreateForm, PlayerEditForm, PlayerUploadForm
from players.models import Player
from players.services import import_players_from_file
from tournaments.models import Tournament


class TournamentPlayersView(AdminRequiredMixin, TemplateView):
    template_name = "players/tournament_players.html"

    def get_tournament(self):
        return get_object_or_404(Tournament, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        players = tournament.players.order_by("name")
        context["tournament"] = tournament
        context["upload_form"] = kwargs.get("upload_form", PlayerUploadForm())
        context["create_form"] = kwargs.get("create_form", PlayerCreateForm(tournament=tournament))
        context["player_cards"] = [
            {"player": player, "form": PlayerEditForm(instance=player, tournament=tournament, prefix=f"player-{player.pk}")}
            for player in players
        ]
        return context

    def post(self, request, *args, **kwargs):
        tournament = self.get_tournament()
        action = request.POST.get("action")
        if action == "upload":
            upload_form = PlayerUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                try:
                    imported = import_players_from_file(tournament, upload_form.cleaned_data["file"])
                except ValueError as exc:
                    upload_form.add_error("file", str(exc))
                    return self.render_to_response(self.get_context_data(upload_form=upload_form))
                messages.success(request, f"Imported or updated {len(imported)} players.")
                return redirect("tournament-players", pk=tournament.pk)
            return self.render_to_response(self.get_context_data(upload_form=upload_form))

        if action == "create_manual":
            create_form = PlayerCreateForm(request.POST, request.FILES, tournament=tournament)
            if create_form.is_valid():
                player = create_form.save(commit=False)
                player.tournament = tournament
                player.sport_type = tournament.sport_type
                player.save()
                messages.success(request, f"Added {player.name}.")
                return redirect("tournament-players", pk=tournament.pk)
            return self.render_to_response(self.get_context_data(create_form=create_form))

        player = get_object_or_404(Player, pk=request.POST.get("player_id"), tournament=tournament)
        form = PlayerEditForm(request.POST, request.FILES, instance=player, tournament=tournament, prefix=f"player-{player.pk}")
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {player.name}.")
            return redirect("tournament-players", pk=tournament.pk)
        context = self.get_context_data()
        for card in context["player_cards"]:
            if card["player"].pk == player.pk:
                card["form"] = form
        return self.render_to_response(context)

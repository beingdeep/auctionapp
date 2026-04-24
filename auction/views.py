from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView

from auction.services import (
    all_captains_online,
    auction_state,
    equally_distribute_unsold_players,
    get_presence_rows,
    manually_distribute_unsold_players,
    mark_round_sold,
    mark_round_unsold,
    place_bid,
    recycle_unsold_players,
    select_random_player,
    start_tournament_auction,
)
from tournaments.models import Tournament


class AuctionAccessMixin(LoginRequiredMixin):
    def get_tournament(self):
        return get_object_or_404(Tournament, pk=self.kwargs["pk"])

    def has_access(self, tournament):
        user = self.request.user
        return bool(user.is_admin() or tournament.teams.filter(captain=user).exists())

    def is_controller(self, tournament):
        user = self.request.user
        return bool(user.is_super_admin() or tournament.auctioneer_id == user.id)

    def dispatch(self, request, *args, **kwargs):
        tournament = self.get_tournament()
        if not self.has_access(tournament):
            return HttpResponseForbidden("You do not have access to this auction.")
        return super().dispatch(request, *args, **kwargs)


class AuctionLobbyView(AuctionAccessMixin, TemplateView):
    template_name = "auction/lobby.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        context["tournament"] = tournament
        context["presence_rows"] = get_presence_rows(tournament)
        context["all_captains_online"] = all_captains_online(tournament)
        context["is_controller"] = self.is_controller(tournament)
        context["needs_confirmation"] = tournament.start_date != timezone.localdate() and tournament.status != "live"
        return context

    def post(self, request, *args, **kwargs):
        tournament = self.get_tournament()
        if not self.is_controller(tournament):
            return HttpResponseForbidden("Only the auctioneer can start the auction.")

        action = request.POST.get("action")
        if action == "start_auction":
            start_tournament_auction(tournament)
            messages.success(request, "Auction lobby is live. Wait until all captains are online.")
        elif action == "go_live":
            if not all_captains_online(tournament):
                messages.error(request, "All captains must be online before entering the live auction.")
                return redirect("auction-lobby", pk=tournament.pk)
            return redirect("auction-live", pk=tournament.pk)
        return redirect("auction-lobby", pk=tournament.pk)


class AuctionStateView(AuctionAccessMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        return JsonResponse(auction_state(self.get_tournament()))


class AuctionLiveView(AuctionAccessMixin, TemplateView):
    template_name = "auction/live.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        context["tournament"] = tournament
        context["is_controller"] = self.is_controller(tournament)
        context["state"] = auction_state(tournament)
        context["captain_team"] = tournament.teams.filter(captain=self.request.user).first()
        context["unsold_players"] = tournament.players.filter(status="unsold", assigned_team__isnull=True).order_by("name")
        context["teams"] = tournament.teams.order_by("team_slot")
        context["captain_players"] = context["captain_team"].players.order_by("-sold_for", "name") if context["captain_team"] else []
        return context

    def post(self, request, *args, **kwargs):
        tournament = self.get_tournament()
        action = request.POST.get("action")
        try:
            if action == "select_random_player":
                if not self.is_controller(tournament):
                    return HttpResponseForbidden("Only the auctioneer can select players.")
                select_random_player(tournament)
                messages.success(request, "A new player has entered the live auction.")
            elif action == "quick_bid":
                place_bid(tournament, request.user)
                messages.success(request, "Your live bid has been placed.")
            elif action == "custom_bid":
                place_bid(tournament, request.user, custom_amount=request.POST.get("custom_amount"))
                messages.success(request, "Your custom bid has been placed.")
            elif action == "sold":
                if not self.is_controller(tournament):
                    return HttpResponseForbidden("Only the auctioneer can sell the player.")
                mark_round_sold(tournament)
                messages.success(request, "Player marked as sold.")
            elif action == "unsold":
                if not self.is_controller(tournament):
                    return HttpResponseForbidden("Only the auctioneer can mark a player unsold.")
                mark_round_unsold(tournament)
                messages.success(request, "Player marked as unsold.")
            elif action == "recycle_unsold":
                if not self.is_controller(tournament):
                    return HttpResponseForbidden("Only the auctioneer can recycle unsold players.")
                recycled = recycle_unsold_players(tournament)
                messages.success(request, f"Recycled {recycled} unsold players back into the pool.")
            elif action == "equal_distribute":
                if not self.is_controller(tournament):
                    return HttpResponseForbidden("Only the auctioneer can distribute unsold players.")
                assigned = equally_distribute_unsold_players(tournament)
                messages.success(request, f"Assigned {assigned} unsold players based on available squad spots.")
            elif action == "manual_distribute":
                if not self.is_controller(tournament):
                    return HttpResponseForbidden("Only the auctioneer can distribute unsold players.")
                team_mapping = {
                    key.replace("assign_player_", ""): value
                    for key, value in request.POST.items()
                    if key.startswith("assign_player_")
                }
                assigned = manually_distribute_unsold_players(tournament, team_mapping)
                messages.success(request, f"Manually assigned {assigned} unsold players.")
        except ValidationError as exc:
            messages.error(request, getattr(exc, "message", str(exc)))
        return redirect("auction-live", pk=tournament.pk)

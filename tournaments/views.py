from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.utils import timezone

from accounts.views import AdminRequiredMixin
from tournaments.forms import TournamentForm
from tournaments.models import Tournament


class TournamentListView(AdminRequiredMixin, ListView):
    model = Tournament
    template_name = "tournaments/tournament_list.html"
    context_object_name = "tournaments"

    def get_queryset(self):
        queryset = Tournament.objects.prefetch_related("assigned_admins").order_by("start_date", "name")
        if self.request.GET.get("view") == "previous":
            return queryset.filter(start_date__lt=timezone.localdate())
        return queryset.filter(start_date__gte=timezone.localdate())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_previous"] = self.request.GET.get("view") == "previous"
        return context


class TournamentCreateView(AdminRequiredMixin, CreateView):
    model = Tournament
    form_class = TournamentForm
    template_name = "tournaments/tournament_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.user not in self.object.assigned_admins.all():
            self.object.assigned_admins.add(self.request.user)
        self.object.sync_team_slots()
        messages.success(self.request, "Tournament created. Add players and teams next.")
        return response

    def get_success_url(self):
        return reverse("tournament-detail", kwargs={"pk": self.object.pk})


class TournamentUpdateView(AdminRequiredMixin, UpdateView):
    model = Tournament
    form_class = TournamentForm
    template_name = "tournaments/tournament_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.can_be_managed_by(request.user):
            return HttpResponseForbidden("Only the super admin can edit previous tournaments.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.sync_team_slots()
        messages.success(self.request, "Tournament updated.")
        return response

    def get_success_url(self):
        return reverse("tournament-detail", kwargs={"pk": self.object.pk})


class TournamentDeleteView(AdminRequiredMixin, DeleteView):
    model = Tournament
    template_name = "tournaments/tournament_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_super_admin():
            return HttpResponseForbidden("Only the super admin can delete tournaments.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(self.request, "Tournament deleted.")
        return reverse("tournament-list")


class TournamentDetailView(AdminRequiredMixin, DetailView):
    model = Tournament
    template_name = "tournaments/tournament_detail.html"
    context_object_name = "tournament"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        context["can_edit"] = tournament.can_be_managed_by(self.request.user)
        context["can_delete"] = self.request.user.is_super_admin()
        context["teams"] = tournament.teams.select_related("captain").order_by("team_slot")
        context["players_count"] = tournament.players.count()
        return context

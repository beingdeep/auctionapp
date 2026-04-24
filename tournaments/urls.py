from django.urls import path

from tournaments.views import (
    TournamentCreateView,
    TournamentDeleteView,
    TournamentDetailView,
    TournamentListView,
    TournamentUpdateView,
)

urlpatterns = [
    path("", TournamentListView.as_view(), name="tournament-list"),
    path("new/", TournamentCreateView.as_view(), name="tournament-create"),
    path("<int:pk>/", TournamentDetailView.as_view(), name="tournament-detail"),
    path("<int:pk>/edit/", TournamentUpdateView.as_view(), name="tournament-edit"),
    path("<int:pk>/delete/", TournamentDeleteView.as_view(), name="tournament-delete"),
]

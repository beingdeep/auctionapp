from django.urls import path

from players.views import TournamentPlayersView

urlpatterns = [
    path("tournaments/<int:pk>/players/", TournamentPlayersView.as_view(), name="tournament-players"),
]

from django.urls import path

from teams.views import TournamentTeamsView

urlpatterns = [
    path("tournaments/<int:pk>/teams/", TournamentTeamsView.as_view(), name="tournament-teams"),
]

from django.urls import path

from auction.views import AuctionLobbyView, AuctionLiveView, AuctionStateView

urlpatterns = [
    path("tournaments/<int:pk>/auction/", AuctionLobbyView.as_view(), name="auction-lobby"),
    path("tournaments/<int:pk>/auction/live/", AuctionLiveView.as_view(), name="auction-live"),
    path("tournaments/<int:pk>/auction/state/", AuctionStateView.as_view(), name="auction-state"),
]

from django.urls import path

from .consumers import AuctionConsumer

websocket_urlpatterns = [
    path("ws/auction/", AuctionConsumer.as_asgi()),
]

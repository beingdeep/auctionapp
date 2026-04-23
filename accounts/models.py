from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    CAPTAIN = "captain", "Captain"
    AUCTIONEER = "auctioneer", "Auctioneer"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_captain(self) -> bool:
        return self.role == UserRole.CAPTAIN

    def is_auctioneer(self) -> bool:
        return self.role == UserRole.AUCTIONEER

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    CAPTAIN = "captain", "Captain"
    AUCTIONEER = "auctioneer", "Auctioneer"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.ADMIN)
    temp_password_expires_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_accounts",
    )

    def is_admin(self) -> bool:
        return self.is_superuser or self.role == UserRole.ADMIN

    def is_captain(self) -> bool:
        return self.role == UserRole.CAPTAIN

    def is_auctioneer(self) -> bool:
        return self.role == UserRole.AUCTIONEER or self.is_admin()

    def is_super_admin(self) -> bool:
        return self.is_superuser or self.username == "admin"

    def temporary_password_is_valid(self) -> bool:
        return not self.temp_password_expires_at or timezone.now() <= self.temp_password_expires_at

    def is_online(self) -> bool:
        return bool(self.last_seen_at and self.last_seen_at >= timezone.now() - timezone.timedelta(seconds=45))

    def display_name(self) -> str:
        return self.get_full_name() or self.username

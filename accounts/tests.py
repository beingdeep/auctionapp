from django.test import RequestFactory, TestCase

from accounts.models import User, UserRole
from accounts.permissions import IsAdmin, IsAuctioneer, IsCaptain


class PermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(username="admin", password="x", role=UserRole.ADMIN)
        self.auctioneer = User.objects.create_user(username="auctioneer", password="x", role=UserRole.AUCTIONEER)
        self.captain = User.objects.create_user(username="captain", password="x", role=UserRole.CAPTAIN)

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_role_permissions(self):
        self.assertTrue(IsAdmin().has_permission(self._request(self.admin), None))
        self.assertFalse(IsAdmin().has_permission(self._request(self.captain), None))
        self.assertTrue(IsAuctioneer().has_permission(self._request(self.auctioneer), None))
        self.assertTrue(IsCaptain().has_permission(self._request(self.captain), None))

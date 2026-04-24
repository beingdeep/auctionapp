from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from accounts.models import User, UserRole
from accounts.permissions import IsAdmin, IsAuctioneer, IsCaptain
from accounts.views import ensure_default_admin


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


class LoginFlowTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_login_page_is_the_first_page(self):
        response = self.client.get("/")

        self.assertRedirects(response, reverse("login"))

    def test_login_page_bootstraps_default_admin(self):
        self.client.get(reverse("login"))

        user = User.objects.get(username="admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertTrue(user.check_password("admin"))

    def test_default_admin_can_log_in(self):
        ensure_default_admin()

        response = self.client.post(
            reverse("login"),
            {"username": "admin", "password": "admin"},
        )

        self.assertRedirects(response, reverse("dashboard"))

    def test_super_admin_can_open_admin_management(self):
        ensure_default_admin()
        self.client.post(reverse("login"), {"username": "admin", "password": "admin"})

        response = self.client.get(reverse("admin-management"))

        self.assertEqual(response.status_code, 200)

    def test_regular_admin_cannot_open_admin_management(self):
        User.objects.create_user(username="ops", password="pw", role=UserRole.ADMIN)
        self.client.post(reverse("login"), {"username": "ops", "password": "pw"})

        response = self.client.get(reverse("admin-management"))

        self.assertEqual(response.status_code, 403)

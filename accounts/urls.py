from django.urls import path

from accounts.views import AdminLoginView, AdminLogoutView, AdminManagementView, DashboardView, PresencePingView, RootRedirectView

urlpatterns = [
    path("", RootRedirectView.as_view(), name="root"),
    path("login/", AdminLoginView.as_view(), name="login"),
    path("logout/", AdminLogoutView.as_view(), name="logout"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("admins/", AdminManagementView.as_view(), name="admin-management"),
    path("presence/ping/", PresencePingView.as_view(), name="presence-ping"),
]

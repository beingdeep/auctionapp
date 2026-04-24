from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import RedirectView, TemplateView
from django.db.models import Count

from accounts.forms import AdminUserCreateForm, AuctionAuthenticationForm
from accounts.models import User, UserRole
from tournaments.models import Tournament


def ensure_default_admin() -> None:
    user, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "role": UserRole.ADMIN,
            "is_staff": True,
            "is_superuser": True,
            "email": "admin@example.com",
        },
    )
    if created:
        user.set_password("admin")
        user.save(update_fields=["password"])


class RootRedirectView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return reverse("dashboard")
        return reverse("login")


class AdminLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = AuctionAuthenticationForm
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        ensure_default_admin()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.get_user())
        self.request.user.last_seen_at = timezone.now()
        self.request.user.save(update_fields=["last_seen_at"])
        return redirect("dashboard")


class AdminLogoutView(LogoutView):
    next_page = "login"


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return bool(self.request.user.is_authenticated and self.request.user.is_admin())


class SuperAdminRequiredMixin(AdminRequiredMixin):
    def test_func(self):
        return bool(self.request.user.is_authenticated and self.request.user.is_super_admin())


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_admin():
            context["upcoming_count"] = Tournament.objects.filter(start_date__gte=timezone.localdate()).count()
            context["previous_count"] = Tournament.objects.filter(start_date__lt=timezone.localdate()).count()
            context["admin_count"] = User.objects.filter(role=UserRole.ADMIN).count()
        else:
            context["captain_teams"] = user.teams.select_related("tournament").order_by("tournament__start_date")
        return context


class AdminManagementView(SuperAdminRequiredMixin, TemplateView):
    template_name = "accounts/admin_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AdminUserCreateForm()
        context["admins"] = User.objects.filter(role=UserRole.ADMIN).annotate(
            managed_total=Count("assigned_tournaments")
        ).order_by("-is_superuser", "username")
        return context

    def post(self, request, *args, **kwargs):
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            form.save(created_by=request.user)
            messages.success(request, "New admin account created.")
            return redirect("admin-management")
        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)


class PresencePingView(LoginRequiredMixin, RedirectView):
    permanent = False
    query_string = False
    pattern_name = "dashboard"

    def get(self, request, *args, **kwargs):
        request.user.last_seen_at = timezone.now()
        request.user.save(update_fields=["last_seen_at"])
        return JsonResponse({"ok": True, "last_seen_at": request.user.last_seen_at.isoformat()})

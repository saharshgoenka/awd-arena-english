from django.urls import path, include
from django.http import HttpResponse
from hr import views as hr_views

urlpatterns = [
    path("", hr_views.home, name="home"),
    path(
        "robots.txt",
        lambda request: HttpResponse(
            "User-agent: *\nDisallow: /debug/env\nDisallow: /admin\n",
            content_type="text/plain",
        ),
        name="robots_txt",
    ),
    path("about/", hr_views.about, name="about"),
    path("help/", hr_views.help_page, name="help"),
    path("status/", hr_views.status_page, name="status"),
    path("api/", hr_views.api_discovery, name="api_discovery"),
    path("login/", hr_views.login_view, name="login"),
    path("logout/", hr_views.logout_view, name="logout"),
    path("dashboard/", hr_views.dashboard, name="dashboard"),
    path("health/", hr_views.health, name="health"),
    path("api/diagnostics/", hr_views.diagnostics_info, name="diagnostics_info"),
    # Un-advertised debug endpoint (NOT listed in /api discovery). Serves the
    # verbose runtime-env dump directly for flag_2 (A05).
    path("debug/env", hr_views.diagnostics_info, name="debug_env"),
    path("exports/encrypted", hr_views.exports_encrypted, name="exports_encrypted"),
    path("hr/", include("hr.urls")),
]

from django.urls import path, include
from hr import views as hr_views

urlpatterns = [
    path("login/", hr_views.login_view, name="login"),
    path("logout/", hr_views.logout_view, name="logout"),
    path("dashboard/", hr_views.dashboard, name="dashboard"),
    path("health/", hr_views.health, name="health"),
    # flag_2: debug endpoint — no auth; patch removes this line
    path("__debug__/info/", hr_views.debug_info, name="debug_info"),
    path("hr/", include("hr.urls")),
]

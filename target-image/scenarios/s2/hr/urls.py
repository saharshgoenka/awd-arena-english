from django.urls import path
from . import views

urlpatterns = [
    path("staff/reports/",    views.staff_reports,    name="staff_reports"),
    path("employees/",        views.employee_list,    name="employee_list"),
    path("employees/<int:pk>/", views.employee_detail, name="employee_detail"),
    path("profile/secret/",   views.profile_secret,   name="profile_secret"),
    path("search/",           views.employee_search,  name="employee_search"),
    path("payroll/",          views.payroll,          name="payroll"),
]

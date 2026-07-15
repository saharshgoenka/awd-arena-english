from django.urls import path
from . import views

urlpatterns = [
    path("staff/reports/",    views.staff_reports,    name="staff_reports"),
    path("reports/",          views.my_reports,       name="my_reports"),
    path("reports/<int:pk>/", views.report_detail,    name="report_detail"),
    path("employees/",        views.employee_list,    name="employee_list"),
    path("employees/<int:pk>/", views.employee_detail, name="employee_detail"),
    path("profile/secret/",   views.profile_secret,   name="profile_secret"),
    path("api/search/",      views.employee_search_api, name="employee_search_api"),
    path("search/",           views.employee_search,  name="employee_search"),
    path("payroll/",          views.payroll,          name="payroll"),
]
